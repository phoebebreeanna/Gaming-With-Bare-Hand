# HandMouse - Gesture Control

Control your mouse, keyboard, and games using only your hand and a webcam.
No hardware required - powered by MediaPipe, OpenCV, and PySide6.

---

## Features

- **Mouse control** - move cursor, left/right click, drag, and scroll
- **Subway Surfers mode** - tilt and swipe gestures mapped to arrow keys
- **Car Racing mode** - two-hand tilt steering with thumbs-up accelerate/brake
- **Free slot** - customise with your own gesture logic
- **Live camera feed** with real-time hand skeleton overlay
- **Multi-camera support** - detect and switch cameras at runtime
- **Zone calibration** - choose small, medium, or large movement zones

---

## Requirements

- Python **3.9 or higher**
- A webcam or external USB camera
- The `hand_landmarker.task` model file (see Installation below)

Python packages (all in `requirements.txt`):

- PySide6 >= 6.5.0
- opencv-python >= 4.8.0
- mediapipe >= 0.10.0
- pyautogui >= 0.9.54
- numpy >= 1.24.0
- torch >= 2.0.0
- joblib >= 1.3.0

> **macOS Apple Silicon**: All packages run natively. No extra steps needed.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Gaming-With-Bare-Hand.git
cd Gaming-With-Bare-Hand
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
```

Activate it:

```bash
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the MediaPipe hand landmark model

Go to: https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker

Download `hand_landmarker.task` and place it in the `logic/` folder:

```
Gaming-With-Bare-Hand/
└── logic/
    └── hand_landmarker.task
```

### 5. Game mode ML models (optional)

For Subway Surfers and Car Racing, place these files in `logic/`:

```
logic/gesture_model_subway.pt
logic/label_encoder_subway.pkl
logic/gesture_model_racing.pt
logic/label_encoder_racing.pkl
```

If missing, those game modes are silently disabled. Mouse mode works without them.

---

## Running

```bash
python main.py
```

A 3-second splash screen appears, then the main interface loads.

---

## How to use

### Step 1 - Select a camera

Use the **Camera** dropdown at the top of the Home page.
Click **Refresh** if a camera was connected after the app started.

### Step 2 - Start tracking

Click **Start**. The app runs through these stages automatically:

- **Intro** - short intro slide. Raise Thumbs Up to skip.
- **Zone Intro** - explains zone sizes. Raise Thumbs Up to skip.
- **Zone Pick** - show 1, 2, or 3 fingers and hold 5 seconds to choose Small / Medium / Large.
- **Gesture Guide** - quick gesture reminder. Raise Thumbs Up to skip.
- **Distance Check** - hold your hand at arm's length until the bar fills green (3 seconds).
- **Running** - full gesture control is now active.

### Step 3 - Gesture reference

**Mouse Mode**

| Gesture | Action |
| --- | --- |
| Index finger only | Move cursor |
| Thumb + Middle pinch, held under 0.5s | Left click |
| Thumb + Middle pinch, held over 0.5s | Drag |
| Thumb + Ring pinch | Right click |
| Index + Middle + Ring up | Scroll up |
| All fingers curled (fist) | Scroll down |

**Meta gestures - hold the gesture for the listed duration**

| Gesture | Hold | Action |
| --- | --- | --- |
| Open palm | 3s | Pause tracking |
| Both peace signs (two hands) | 3s | Resume tracking |
| Shaka | 3s | Recalibrate movement zone |
| Metal sign | 3s | Show gesture guide |
| Both fists (two hands) | 3s | Close session |

**Switching game modes while running**

Show one fist on one hand and N fingers on the other, hold 5 seconds:

| Fingers | Mode |
| --- | --- |
| 1 finger | Mouse mode (default) |
| 2 fingers | Subway Surfers |
| 3 fingers | Car Racing |
| 4 fingers | Free slot |

---

## Project structure

```
Gaming-With-Bare-Hand/
├── main.py                        # App entry point
├── requirements.txt
├── README.md
├── logic/
│   ├── __init__.py
│   ├── hand_controller.py         # QThread - gesture detection + state machine
│   ├── virtual_mouse_main.py      # Original standalone script (reference)
│   ├── hand_landmarker.task       # MediaPipe model (download separately)
│   ├── gesture_model_subway.pt    # Subway Surfers model (optional)
│   ├── label_encoder_subway.pkl
│   ├── gesture_model_racing.pt    # Car Racing model (optional)
│   └── label_encoder_racing.pkl
└── ui/
    ├── welcome_screen.py
    ├── main_menu.py               # Sidebar + home page with live feed
    ├── user_guide.py
    ├── gesture_guide.py
    ├── distance_check.py
    ├── zone_setup.py
    └── game_mode.py
```

---

## Tech stack

- **PySide6** - desktop UI framework (Qt 6)
- **MediaPipe** - hand landmark detection (21-point skeleton)
- **OpenCV** - camera capture, frame processing, skeleton overlay
- **PyTorch** - GestureNet neural network for game mode classification
- **PyAutoGUI** - mouse movement, clicks, keyboard input
- **NumPy** - vector math for gesture calculations

---

## Troubleshooting

**No camera detected**
Make sure your camera is not in use by another app. Click Refresh in the app.

**hand_landmarker.task not found**
Download the file and place it in `logic/` - see Installation step 4.

**Game modes not working**
The `.pt` and `.pkl` model files must be in `logic/`. Mouse mode works without them.

**Tracking drifts**
Use the Shaka gesture (hold 3s) to recalibrate. Make sure lighting is even.

**App crashes on exit**
Stop tracking first with the Stop button, or use the Exit button inside the app.

---

## License

MIT License - free to use, modify, and distribute.
