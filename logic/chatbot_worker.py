from PySide6.QtCore import QThread, Signal


class ChatbotQueryThread(QThread):
    answer_ready = Signal(str)
    answer_failed = Signal(str)

    def __init__(self, question: str, parent=None):
        super().__init__(parent)
        self.question = question

    def run(self):
        from logic.chatbot.rag_service import ask_realtime, ChatbotUnavailableError
        try:
            answer = ask_realtime(self.question)
        except ChatbotUnavailableError as e:
            self.answer_failed.emit(str(e))
            return
        except Exception:
            self.answer_failed.emit(
                "Something went wrong answering that - please try again."
            )
            return

        self.answer_ready.emit(answer)


class ModelDownloadThread(QThread):
    progress = Signal(int, int)
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, cancel_event, parent=None):
        super().__init__(parent)
        self.cancel_event = cancel_event

    def run(self):
        from logic.chatbot.rag_service import download_model, DownloadCancelled
        try:
            download_model(
                progress_cb=lambda d, t: self.progress.emit(d, t),
                cancel_event=self.cancel_event,
            )
        except DownloadCancelled:
            return
        except Exception as e:
            self.failed.emit(str(e))
            return

        self.finished_ok.emit()
