# HandMouse - Gesture Control

Control your mouse, keyboard, and games using only your hand and a webcam.
No hardware required - powered by MediaPipe, OpenCV, PyTorch, and PySide6.

---

## Features

- **Mouse mode** - move cursor, left/right click, drag, and scroll with hand gestures
- **Subway Surfers mode** - swipe and tilt gestures mapped to arrow keys and space
- **Racing mode** - two-hand tilt steering with thumb-up accelerate/brake and horn/camera actions
- **Open World mode** - 18 gestures mapped to movement (WASD), abilities, team commands, and more
- **Custom model training** - collect gesture data and train your own neural network in-app
- **Live model swap** - switch between Default and Custom model per mode without restarting
- **Key bindings editor** - remap any gesture to any key; locked directional gestures shown read-only
- **Reset All** - restore a mode's key bindings to defaults with one click
- **Live camera feed** with real-time hand skeleton overlay and distance alert
- **Multi-camera support** - enumerate and switch cameras at runtime
- **Zone calibration** - choose Small, Medium, or Large movement zone
- **Dark / Light theme** - full theme toggle across all pages
- **Custom gesture modes** - define and train an entirely new gesture set (not just Mouse/Subway/Racing) from the Train Model page, then select and run it from Settings
- **Train Model Guide** - step-by-step walkthrough (with per-step reference videos/images) covering the full custom-training workflow: collecting samples, preprocessing, training, reviewing, and using your custom model
- **HandBot chatbot** - ask questions from the chat panel; runs fully offline on a bundled local model (auto-downloaded on first use, no setup), or switch to ChatGPT in Settings by adding your own OpenAI API key - no `.env` file needed, the key is stored on-device
- **Status overlay** - optional small status panel that stays visible when you switch to another app/game window
- **Air Hockey mode** - launch the bundled local 2-player air hockey game and drive a paddle with your left-hand wrist position; right hand fires powers by finger count

---

## Requirements

- Python **3.9 or higher**
- A webcam or external USB camera
- The `hand_landmarker.task` model file (see Installation)
- The `hagridv2_gesture_recognizer.task` model file for Open World mode (optional)

Python packages (all in `requirements.txt`):

```
PySide6 >= 6.5.0
opencv-python >= 4.8.0
mediapipe >= 0.10.0
pyautogui >= 0.9.54
numpy >= 1.24.0
torch >= 2.0.0
joblib >= 1.3.0
pynput >= 1.7.0
pandas >= 1.5.0
scikit-learn >= 1.0.0
llama-index >= 0.14.0
llama-index-llms-llama-cpp >= 0.6.0
llama-index-llms-openai >= 0.6.0
llama-index-embeddings-huggingface >= 0.7.0
llama-index-vector-stores-chroma >= 0.5.0
chromadb >= 1.5.0
pygame >= 2.5.0
```

> **macOS Apple Silicon**: All packages run natively. No extra steps needed.

> **HandBot chatbot** works fully offline right after `pip install -r
> requirements.txt` - the local model (Qwen2.5-3B, GGUF format) is downloaded
> automatically the first time you ask a question. To use ChatGPT instead,
> open Settings → AI Backend, select **CHATGPT**, and paste in your own
> OpenAI API key - it's saved on-device, no `.env` file required.

> **Air Hockey mode** needs nothing beyond `pip install -r requirements.txt` -
> `pygame` is installed automatically and the bundled game has no external
> asset files to download.

---

## Installation

There are two ways to get HandMouse running:

- **Option A - Download the installer** (recommended for most users): grab the
  pre-built app from https://handmouse.vercel.app/ and run it directly. No
  Python, virtual environment, or dependencies needed - skip straight to
  [How to use](#how-to-use).
- **Option B - Run from source** (for development or customization): clone the
  repo and set up the Python environment yourself, as below.

### 1. Clone the repository

```bash
git clone https://github.com/your-username/HandMouse.git
cd HandMouse
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
python install_dependencies.py
```

This installs everything in `requirements.txt`. On Windows it first grabs a
prebuilt CPU wheel for `llama-cpp-python` (`pip install llama-cpp-python
--prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu`)
so it doesn't try to compile it from source; on macOS/Linux it just runs
`pip install -r requirements.txt` directly.

### 4. Download the MediaPipe hand landmark model

Download `hand_landmarker.task` from:
https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker

Place it at:

```
logic/hand_landmarker.task
```

### 5. Download the Open World gesture model (optional)

Download `hagridv2_gesture_recognizer.task` from the MediaPipe model card or HaGRID repository.

Place it at:

```
logic/data/hagridv2_gesture_recognizer.task
```

If missing, Open World mode falls back to landmark-only gestures.

### 6. Default ML models

Pre-trained models for Mouse, Subway, and Racing modes are included under `logic/data/`:

```
logic/data/
├── mouse_gesture_model_best.pt
├── mouse_label_encoder.pkl
├── subway_gesture_model_best.pt
├── subway_label_encoder.pkl
├── racing_gesture_model_best.pt
└── racing_label_encoder.pkl
```

Custom-trained models are saved to `logic/data/custom/` via the Train Model page.

### 7. (Optional) Use ChatGPT instead of the local chatbot model

HandBot works out of the box in **Local** mode - the first question you ask
triggers a one-time download of the bundled Qwen2.5-3B GGUF model, then
answers are generated fully offline via `llama.cpp`. The local search index
(`logic/chatbot/chroma_db/`) is also built automatically on first use.

To use **ChatGPT** instead, open Settings → AI Backend, select **CHATGPT**,
and paste your own OpenAI API key into the field below - it's saved to
`logic/app_config.json` on your machine, no `.env` file needed. Switch
between Local and ChatGPT anytime from the same Settings section.

---

## Running

```bash
python main.py
```

or via Make:

```bash
make run
```

A 3-second welcome screen appears, then the main interface loads.

---

## Building the app

A `Makefile` is included for all common tasks.

| Command | Description |
|---|---|
| `make run` | Run the app directly with Python |
| `make build-mac-app` | Build a standalone `.app` bundle for macOS (arm64) |
| `make build-mac-dmg` | Build the `.app` and wrap it in a distributable `.dmg` (requires `brew install create-dmg`) |
| `make build-win` | Build a standalone `.exe` for Windows |
| `make icon-mac` | Generate `hand_gesture_icon.icns` from the source PNG |
| `make icon-win` | Generate `hand_gesture_icon.ico` from the source PNG |
| `make eval` | Run the gesture evaluation suite against `research/dataset/` |
| `make clean` | Remove `build/` and `dist/` |

### macOS app bundle

```bash
make build-mac-dmg
```

Produces `dist/HandMouse.app` and `dist/HandMouse.dmg`. Open the `.dmg` and drag
`HandMouse.app` into Applications, or distribute the `.app` folder directly.
macOS will prompt for camera permission on first launch.

### Windows executable

```bash
make build-win
```

Produces `dist/main/main.exe` (onedir). Distribute the entire `dist/main/` folder.

---

## How to use

### Step 1 - First-time setup

On first launch the setup wizard runs automatically:

1. **Camera Setup** - select your camera and confirm the preview looks correct.
2. **Distance Calibration** - hold your hand at roughly arm's length until the progress bar completes.
3. **Zone Setup** - show 1, 2, or 3 fingers and hold to choose Small / Medium / Large movement zone.

Setup is saved to `logic/app_config.json`. Subsequent launches skip straight to the dashboard.

### Step 2 - Choose a mode and model source

Open **Settings (05)** from the sidebar:

- Click a mode card to select it (Mouse / Subway Surfers / Racing / Open World).
- Toggle **DEFAULT** or **CUSTOM** below each card. Custom is enabled once you have trained a model via Train Model (06).
- Switching Default ↔ Custom takes effect immediately, even while the controller is running.

### Step 3 - Customize key bindings

Open **Key Bindings (07)** from the sidebar:

- Click any key button to remap a gesture - press the desired key to confirm, Escape to cancel.
- Locked gestures (greyed out) use fixed directional logic and cannot be rebound.
- Click **RESET ALL** at the top of a section to restore that mode's default bindings.

### Step 4 - Start tracking

Go to **Home (01)** and click **Start**. The status card shows **Running** when ready.

Use the distance alert (OPTIMAL / TOO FAR / TOO CLOSE) in the camera feed to position your hand correctly.

---

## Gesture reference

### Meta gestures (all modes)

| Gesture | Action |
|---|---|
| Both open palms (2 hands) - hold 3s | Pause controller |
| Both peace signs (2 hands) - hold 3s | Resume from pause |
| Both fists (2 hands) - hold 2s | Exit controller |
| One fist + N fingers (other hand) - hold 3s | Switch game mode (see below) |

### Game mode switching

| Fingers on free hand | Mode |
|---|---|
| 1 | Mouse |
| 2 | Subway Surfers |
| 3 | Racing |
| 4 | Open World |

---

### Mouse mode

| Gesture | Action |
|---|---|
| Index finger up | Move cursor |
| OK sign (thumb + index pinch) - tap | Left click |
| OK sign - hold 0.5s | Drag |
| Middle pinch (thumb + middle) | Right click |
| Index + Middle + Ring up | Scroll up |
| Fist | Scroll down |

---

### Subway Surfers mode

| Gesture | Key | Action |
|---|---|---|
| Two fingers up | ↑ | Jump |
| Two fingers down | ↓ | Slide |
| Two fingers left | ← | Swipe left |
| Two fingers right | → | Swipe right |
| Metal sign (devil horns) | Space | Jump boost |

---

### Racing mode

| Gesture | Key | Action |
|---|---|---|
| Right thumb up | ↑ | Accelerate |
| Left thumb up | ↓ | Brake |
| Both hands tilt left | ← | Steer left |
| Both hands tilt right | → | Steer right |
| Right index + middle forward (hold) | H | Horn |
| Left index + middle forward (tap) | C | Change camera |

---

### Open World mode

Default key bindings - all rebindable via Key Bindings except the locked movement gestures.

| Gesture | Default Key | Action |
|---|---|---|
| Peace sign pointing up *(locked)* | W | Move forward |
| Peace sign pointing down *(locked)* | S | Move backward |
| Gun pose left/right *(locked)* | A / D | Strafe |
| Thumbs up | Shift | Dodge |
| Open palm | Space | Jump |
| L-sign (thumb + index) | E | Ability |
| OK sign | F | Interact |
| Call sign | R | Skill |
| Thumbs down | Q | Alt skill |
| Holy / spread hand | Esc | Menu / escape |
| Grip / fist-clench | Alt | Alt action |
| Index finger up | 1 | Teammate 1 |
| Peace sign | 2 | Teammate 2 |
| Three fingers up | 3 | Teammate 3 |
| Four fingers up | 4 | Teammate 4 |
| Inverted peace sign | T | Extra 1 |
| Three-three pose | Tab | Map / Tab |
| Three-two pose | G | Extra 2 |

### Air Hockey mode

Air Hockey drives a bundled local pygame game (`hockey_game/`) instead of the
keyboard/mouse directly - HandMouse launches it as its own window and then
sends synthetic keypresses to it, the same way Subway Surfers and Racing mode
work.

1. Open the **08 - AIR HOCKEY** tab in the sidebar and click **LAUNCH AIR
   HOCKEY**. This opens the game in its own window (the button disables
   while it's running).
2. Go to **Settings**, select the **AIR HOCKEY** card in Game Mode to make it
   the active mode, then start tracking as usual. Make sure the air hockey
   game window has focus so it receives the keypresses.

| Gesture | Controls |
|---|---|
| Left hand wrist position | Moves the paddle in that direction (relative to a fixed reference point, with a deadzone) |
| Right hand - number of fingers raised (1-5) | Fires a power: 1 Shield, 2 Freeze, 3 Double Puck, 4 Slow Puck, 5 Speed Puck |

The game supports local 2-player play from one camera: hands detected on the
left half of the camera frame control Player 1 (WASD / 1-5), hands on the
right half control Player 2 (Arrow keys / 6-0).

---

## Custom model training

1. Open **Train Model (06)** from the sidebar.
2. Select a mode (Mouse / Subway / Racing).
3. Use the **Collect** tab to record gesture samples - point the camera at your hand and record each gesture class.
4. Use the **Train** tab to train the neural network on your collected data.
5. Once training completes, go to **Settings (05)** and switch the mode's source to **CUSTOM**.

Custom models are saved to `logic/data/custom/` and are not tracked by git.

New to the workflow? **Train Model Guide (04)** in the sidebar walks through
all five steps above with reference videos and images for each one.

---

## Marketing page

`index.html` is a self-contained static landing page for the project - no build step or server needed, just open it in a browser.

It covers the project pitch, feature highlights, the five-stage processing pipeline, and team credits. It is independent of the Python app and is not bundled into the desktop build.

---

## Research

The `research/` folder contains everything used to evaluate the gesture recognition systems.

```
research/
├── evaluate.py          # Evaluation script - runs both rule-based and neural models
├── hand_landmarker.task # MediaPipe model used during evaluation
├── dataset/             # Labelled images for each gesture class
│   ├── left_click/
│   ├── right_click/
│   ├── scroll_up/
│   ├── scroll_down/
│   ├── release_left_click/
│   └── release_right_click/
└── eval_results/        # Output charts and CSV files written by evaluate.py
```

Run the evaluation with:

```bash
make eval
```

Outputs saved to `research/eval_results/`:
- `evaluation.png` - confusion matrix, per-label accuracy, and latency charts
- `comparison.png` - rule-based vs neural side-by-side (when both are available)
- `misclassified_rule.png` / `misclassified_neural.png` - up to 5 failure examples per system
- `results.json` - full metrics in JSON
- `per_image_rule.csv` / `per_image_neural.csv` - per-image prediction log

---

## Project structure

```
HandMouse/
├── main.py                        # App entry point + event filter
├── Makefile                       # Build, run, eval, and icon generation
├── requirements.txt
├── README.md
├── index.html                     # Static marketing / landing page
├── research/                      # Evaluation scripts and dataset (see Research above)
├── logic/
│   ├── hand_controller.py         # QThread - gesture detection + state machine
│   ├── hand_utils.py              # Shared geometry helpers, drawing, constants
│   ├── gesture_net.py             # GestureNet architecture + load/run helpers
│   ├── gesture_pipeline.py        # Data collection + model training pipeline
│   ├── app_config.py              # Persistent JSON config (zone, mode, bindings…)
│   ├── chatbot_worker.py          # QThread wrapper for chatbot queries
│   ├── chatbot/
│   │   ├── rag_service.py         # Local (llama.cpp) + ChatGPT (OpenAI) RAG pipeline
│   │   ├── data/                  # Chatbot corpus (about.md, user_guide.md)
│   │   ├── models/                # Auto-downloaded local GGUF model (git-ignored)
│   │   └── chroma_db/             # Auto-built vector index (git-ignored)
│   ├── air_hockey_launcher.py     # Launches hockey_game/ as a subprocess
│   ├── hand_landmarker.task       # MediaPipe model (download separately)
│   ├── modes/
│   │   ├── mouse_mode.py          # MouseModeMixin
│   │   ├── subway_mode.py         # SubwayModeMixin
│   │   ├── racing_mode.py         # RacingModeMixin
│   │   ├── open_world_mode.py     # OpenWorldModeMixin
│   │   ├── air_hockey_mode.py     # AirHockeyModeMixin - wrist-tracked paddle + skill gestures
│   │   └── custom_mode.py         # CustomModeMixin - runs user-trained custom gesture sets
│   ├── conf/
│   │   ├── mouse_control.conf
│   │   ├── subway_surfers.conf
│   │   └── racing.conf
│   └── data/
│       ├── hand_landmarker.task
│       ├── hagridv2_gesture_recognizer.task
│       ├── mouse_gesture_model_best.pt
│       ├── subway_gesture_model_best.pt
│       ├── racing_gesture_model_best.pt
│       └── custom/                # User-trained models (git-ignored)
└── ui/
    ├── welcome_screen.py
    ├── main_menu.py               # Sidebar + home dashboard
    ├── user_guide.py
    ├── gesture_guide.py
    ├── train_model_guide.py       # Train Model Guide page - step-by-step walkthrough w/ videos
    ├── game_mode.py               # Settings page (mode, camera, model source)
    ├── key_bindings.py            # Key binding editor
    ├── pipeline_ui.py             # Train Model page
    ├── mainmenu_setup.py
    ├── mainmenu_calibration.py
    ├── mainmenu_zone.py
    ├── mainmenu_camera.py
    ├── handbot.py                 # HandBot guide + chat panel
    ├── air_hockey_status.py       # Live per-player gesture status panel
    ├── air_hockey_loading.py      # "Switching to Air Hockey" transition overlay
    ├── air_hockey_launch_page.py  # Dedicated sidebar tab - just launches the game
    └── mini_camera_overlay.py     # Optional status overlay shown over other apps/windows

hockey_game/                       # Bundled local 2-player air hockey game (pygame, untouched)
├── main.py                        # Run standalone with `cd hockey_game && python3 main.py`
├── config.py / physics.py / render.py / powers.py / input_handler.py / audio.py
└── README.md                      # Game architecture notes
```

---

## Tech stack

| Library | Role |
|---|---|
| **PySide6** | Desktop UI framework (Qt 6) |
| **MediaPipe** | Hand landmark detection (21-point skeleton) + HaGRIDv2 gesture recognition |
| **OpenCV** | Camera capture, frame processing, skeleton overlay |
| **PyTorch** | GestureNet neural network for game mode classification |
| **pynput** | Low-level keyboard/mouse input (replaces pyautogui for key-hold) |
| **PyAutoGUI** | Mouse movement and click |
| **NumPy** | Vector math for gesture geometry |
| **llama-index + Chroma + llama.cpp** | Local RAG pipeline for HandBot (bundled Qwen2.5-3B GGUF model) |
| **OpenAI API** | Optional ChatGPT backend for HandBot - user-supplied key, stored on-device |
| **pygame** | Powers the bundled Air Hockey game (launched as its own window) |

---

## Troubleshooting

**macOS - camera permission prompt**
On first launch macOS will show a permission dialog: *"main" would like to access the camera*. Click **Allow**. If you missed it or clicked Deny, go to **System Settings → Privacy & Security → Camera**, find **main** in the list, and toggle it on. The app cannot start gesture tracking without camera access.

**macOS - no permission prompt appears**
This can happen if the app was previously blocked before it could request permission. Open **System Settings → Privacy & Security → Camera**, check if the app is listed (possibly toggled off), and enable it manually.

**No camera detected**
Make sure your camera is not in use by another app. Reopen the Settings page - cameras are enumerated on load.

**hand_landmarker.task not found**
Download the file and place it in `logic/` - see Installation step 4.

**Open World gestures not recognised**
Make sure `hagridv2_gesture_recognizer.task` is placed in `logic/data/`. Without it, only the landmark-based movement gestures (WASD) are active.

**Custom model not available**
The Custom button is greyed out until both `.pt` and `.pkl` files exist in `logic/data/custom/`. Train a model first via Train Model (06).

**Gestures triggering my own app UI**
HandMouse filters out gesture-generated keypresses from its own UI automatically via an application-level event filter.

**App crashes on exit**
Stop tracking first with the Stop button, or use the Exit button in the app. Never force-quit while the controller is running.

**Tracking drifts or lags**
Ensure even lighting and a clear background. Retrain a Custom model if the default model does not fit your hand or environment well.

**Chatbot says it's unavailable**
In **Local** mode, make sure the model download finished (Settings shows a progress dialog on first use). In **ChatGPT** mode, make sure a valid OpenAI API key is saved under Settings → AI Backend - switch back to Local if you don't have one.

**Air Hockey gestures aren't registering**
Synthetic keypresses go to whichever window has OS focus, same as Subway Surfers and Racing mode - click into the air hockey game window after launching it, then start tracking. If the LAUNCH button stays greyed out, an air hockey window is still open from a previous launch (or `hockey_game/` is missing from this checkout).

---

## License

MIT License - free to use, modify, and distribute.

---
> Forked and maintained by Phoebe Charleen Breeanna as part of FYP-26-S2-02.

