import threading
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
PERSIST_DIR = Path(__file__).parent / "chroma_db"
MODELS_DIR = Path(__file__).parent / "models"
COLLECTION_NAME = "handmouse_docs"
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
SIMILARITY_CUTOFF = 0.62
SIMILARITY_TOP_K = 40

PRIMARY_MODEL_FILENAME = "qwen2.5-3b-instruct-q4_k_m.gguf"
PRIMARY_MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/"
    "qwen2.5-3b-instruct-q4_k_m.gguf"
)

NOT_FOUND_MESSAGE = "I'm not sure about that - it isn't covered in the guide."


class ChatbotUnavailableError(Exception):
    pass


class DownloadCancelled(Exception):
    pass


def _primary_model_path() -> Path:
    return MODELS_DIR / PRIMARY_MODEL_FILENAME


def is_primary_model_ready() -> bool:
    return _primary_model_path().exists()


def download_model(progress_cb=None, cancel_event: threading.Event = None) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = _primary_model_path()
    tmp = dest.with_suffix(dest.suffix + ".part")

    request = urllib.request.Request(
        PRIMARY_MODEL_URL, headers={"User-Agent": "HandMouse"}
    )
    try:
        with urllib.request.urlopen(request) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(tmp, "wb") as f:
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise DownloadCancelled()
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(downloaded, total)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    tmp.rename(dest)
    return dest


def _build_prompt():
    from llama_index.core import PromptTemplate

    return PromptTemplate(
        "You are a friendly in-app assistant for HANDMOUSE, helping the user set "
        "up and use the app. Information you can use is below - it may be empty.\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Using ONLY the information above, answer the question in plain, natural "
        "language - like a helpful guide talking to the user. Never mention "
        "documents, files, sources, or where the information came from. This is a "
        "strict rule: even if you happen to know the answer from general "
        "knowledge, do NOT use it - if the information above is empty or doesn't "
        "answer the question, respond exactly with: "
        f"\"{NOT_FOUND_MESSAGE}\"\n"
        "Formatting rules: write in Markdown. If the answer has multiple steps, "
        "put each step on its own line as a numbered list item (\"1. ...\", "
        "\"2. ...\"). Keep paragraphs short - a blank line between them. Do not "
        "run steps together in a single paragraph.\n"
        "Question: {query_str}\n"
        "Answer: "
    )


def _build_index():
    import chromadb
    from llama_index.core import Settings, StorageContext, VectorStoreIndex
    from llama_index.core.node_parser import MarkdownNodeParser
    from llama_index.core.readers import SimpleDirectoryReader
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.vector_stores.chroma import ChromaVectorStore

    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
    Settings.llm = None

    documents = SimpleDirectoryReader(
        input_dir=str(DATA_DIR),
        recursive=True,
        required_exts=[".md", ".txt"],
    ).load_data()

    node_parser = MarkdownNodeParser()
    nodes = node_parser.get_nodes_from_documents(documents)
    for node in nodes:
        node.excluded_llm_metadata_keys = list(node.metadata.keys())

    chroma_client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    chroma_collection = chroma_client.get_or_create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    VectorStoreIndex(nodes, storage_context=storage_context, show_progress=False)


def _qwen_completion_to_prompt(completion: str) -> str:
    return f"<|im_start|>user\n{completion}<|im_end|>\n<|im_start|>assistant\n"


def _load_engine():
    import chromadb
    from llama_index.core import Settings, VectorStoreIndex
    from llama_index.core.postprocessor import SimilarityPostprocessor
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.llms.llama_cpp import LlamaCPP
    from llama_index.vector_stores.chroma import ChromaVectorStore

    if not is_primary_model_ready():
        raise ChatbotUnavailableError(
            "The chatbot model hasn't been downloaded yet."
        )

    if not PERSIST_DIR.exists():
        _build_index()

    Settings.embed_model = HuggingFaceEmbedding(
        model_name=EMBED_MODEL_NAME, query_instruction=QUERY_INSTRUCTION
    )
    Settings.llm = LlamaCPP(
        model_path=str(_primary_model_path()),
        temperature=0.2,
        max_new_tokens=512,
        context_window=12000,
        model_kwargs={"n_gpu_layers": -1},
        generate_kwargs={"stop": ["<|im_end|>", "<|im_start|>", "\nQuestion:", "Question:"]},
        completion_to_prompt=_qwen_completion_to_prompt,
        verbose=False,
    )

    chroma_client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    chroma_collection = chroma_client.get_or_create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    index = VectorStoreIndex.from_vector_store(vector_store)
    query_engine = index.as_query_engine(
        similarity_top_k=SIMILARITY_TOP_K,
        node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=SIMILARITY_CUTOFF)],
        response_mode="simple_summarize",
    )
    query_engine.update_prompts({"response_synthesizer:text_qa_template": _build_prompt()})
    return query_engine


_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = _load_engine()
    return _engine


def ask_realtime(question: str) -> str:
    try:
        engine = _get_engine()
    except ImportError as e:
        raise ChatbotUnavailableError(
            "Chatbot dependencies aren't installed - run "
            "`pip install -r requirements.txt`."
        ) from e
    except ChatbotUnavailableError:
        raise
    except Exception as e:
        raise ChatbotUnavailableError(
            "Couldn't load the local chatbot model - please try again."
        ) from e

    try:
        response = engine.query(question)
        return str(response)
    except Exception as e:
        raise ChatbotUnavailableError(
            "The chatbot couldn't answer that - please try again."
        ) from e
