# HANDMOUSE User Guide

HANDMOUSE lets you play PC games using hand gestures captured by your webcam.

## Installation & Environment Setup

Two supported run methods:

| Method | Best for |
|---|---|
| Packaged App | Most users - no Python required |
| Run from Source | Developers / advanced users |

### Method A - Packaged App
- **Windows**: download the HANDMOUSE folder from releases → open `dist/main/`
  → double-click `main.exe`.
- **macOS**: download `main.app` from releases → move to Applications → if
  blocked on first launch, System Preferences → Privacy & Security → "Open
  Anyway" → grant Camera and Accessibility permissions when prompted.

### Method B - Run from Source

**System requirements:**

| Component | Minimum | Recommended |
|---|---|---|
| CPU | Intel Core i5 (8th gen) | Intel Core i7 / Apple M-series |
| RAM | 8 GB | 16 GB |
| GPU | None required (CPU inference) | NVIDIA GPU w/ CUDA (optional, speeds inference) |
| Webcam | USB 720p @ 30 FPS | USB or built-in 1080p @ 60 FPS |
| Display | 1280×720 | 1920×1080+ |
| OS | Windows 10 64-bit | Windows 11, macOS 12+, Ubuntu 22.04 |
| Storage | 500 MB free | 1 GB free (model cache) |

**Python**: 3.10+ required, 3.12 recommended. Download from
python.org. On Windows, check "Add Python to PATH" during install.
Verify: `python --version`.

**Setup commands:**
```
# Clone the repository
git clone <REPOSITORY_URL> handmouse
cd handmouse

# Create and activate virtual environment
python -m venv handmouse_env

# Windows
handmouse_env\Scripts\activate.bat

# macOS / Linux
source handmouse_env/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

**Verify installation** (each should print "OK"):
```
python -c "import PySide6; print('PySide6 OK')"
python -c "import cv2; print('OpenCV OK')"
python -c "import mediapipe; print('MediaPipe OK')"
python -c "import torch; print('PyTorch OK')"
python -c "import pyautogui; print('PyAutoGUI OK')"
```

**Run**: `python main.py`

### Required Model Assets
Both run methods require these files present in `logic/data/`:

| File | Mode |
|---|---|
| `mouse_gesture_model_best.pt` | Mouse Mode |
| `mouse_label_encoder.pkl` | Mouse Mode |
| `subway_gesture_model_best.pt` | Subway Mode |
| `subway_label_encoder.pkl` | Subway Mode |
| `racing_gesture_model_best.pt` | Racing Mode |
| `racing_label_encoder.pkl` | Racing Mode |
| `hagridv2_gesture_recognizer.task` | Open World Mode |

### First Launch
Splash screen with 5-second countdown → "Get Started" or wait → main window
loads → if first launch, Setup Flow starts automatically.

## First-Time Setup Flow

On first launch, the app checks whether you've completed setup before. If not,
you're automatically taken into the mandatory Setup Flow - a 4-step guided
process with a progress indicator. It usually only takes a few minutes:

| Step | Action | Advance |
|---|---|---|
| 01 GUIDE | Read the 4-step overview | Click "LET'S GO" |
| 02 CAMERA | Select camera from dropdown, verify live preview | Click "CONTINUE" |
| 03 CALIBRATE | Hold hand at arm's length until distance bar turns green | Click "CONTINUE" or hold gesture |
| 04 ZONE | Select SMALL / MEDIUM / LARGE detection zone | Click "START TRACKING" or hold gesture |

**Step 03 detail**: raise one hand, palm facing lens, at 50–70 cm from camera.
Hold until Distance Bar is fully green; hold 3s to auto-advance, or click
CONTINUE immediately.

**Step 04 detail - Zone Selection:**

| Zone | Coverage | Sensitivity | Recommended For |
|---|---|---|---|
| SMALL | 10% of frame | High - small movement = large cursor travel | Limited arm/desk space |
| MEDIUM | 20% of frame | Medium - balanced | First-time/general use |
| LARGE | 30% of frame | Low - precise, more arm movement | Ample space / high-res monitors |

Select via showing 1/2/3 fingers to the camera, or click directly. LARGE is
the recommended default. Click "FINISH" or wait 3s to complete and land on Home.

## Application Overview

- Default window size 980×660 px, resizable down to 800×560 px minimum.
- Two-column layout: left sidebar (222 px, navigation) + right content area.
- Sidebar toggled hidden/visible via hamburger (☰) button top-left.

### Sidebar Navigation
- **Menu section**: 01 HOME, 02 USER GUIDE, 03 GESTURE GUIDE
- **Setup section**: 04 SETTING, 05 TRAIN MODEL, 06 KEY BINDINGS

### Theme Switching
Light/Dark mode toggle. **Theme selection does NOT persist - resets to Light
Mode on every app restart** (known limitation, see below).

### Global Key Blocking
While the gesture controller is running, all keyboard input to the HANDMOUSE
UI itself is blocked, so game shortcuts (e.g. arrow keys) don't accidentally
trigger the app's own UI.

### Saved Preferences
All your preferences are saved automatically to a local settings file on your
computer, created the first time you launch the app: setup completion status,
camera choice, calibrated distance, detection zone, key bindings, and game
mode settings.

## Feature Guides (per page)

### 01 - Home Dashboard
Shows: app name, real-time clock, uptime counter; status cards (current mode,
camera, zone, last recognised gesture); gesture output area (name, action,
confidence %); live telemetry (~30 FPS); START/STOP button.

**Start a session**: sidebar → Home → verify mode in CURRENT MODE card (change
via Settings if needed) → position in front of camera → click START.
**Stop**: click STOP, or perform two-peace-sign gesture.
**Exit**: click EXIT, or perform two-fist gesture.

### 02 - User Guide
Read-only reference: what HANDMOUSE is, how detection works, per-mode usage,
performance tips, troubleshooting quick reference. "NEXT" to page through.

### 03 - Gesture Guide
Visual catalogue of all gestures, tabbed by mode: General, Mouse, Subway
Surfers, Open World (racing gestures also covered in the full gesture
reference - see below). Each card: illustration, number, name, description,
mode tag.

### 04 - Game Mode & Settings

**Game modes:**

| Mode | Description |
|---|---|
| MOUSE MODE | Full mouse cursor control |
| SUBWAY SURFERS | Jump, roll, left, right, space key presses |
| RACING | Held accelerate/brake with wrist-angle steering |
| OPEN WORLD | Action-game gesture set |

Click a mode card to switch - saved immediately.

**Mouse Control Settings** (Mouse Mode):
- Mouse In Game toggle - enables Devil Horn gesture overlay across all modes.
- Mouse Side - LEFT/RIGHT hand for cursor control; LEFT places detection zone
  on the left.
- Cursor Point - TIP (fingertip) or KNUCKLE (default, more stable).

**Camera Selection**: dropdown of devices; takes effect next session start.

**Detection Zone**: SMALL/MEDIUM/LARGE; takes effect immediately, autosaved.

**Model Source (per mode)**: DEFAULT (bundled) or CUSTOM (greyed out until a
custom model has been trained for that mode).

**Performance Display**: real-time FPS and gesture detection latency.

### 05 - Train Model (Custom Gestures)
Steps:
1. Select mode to train (Mouse, Subway, or Racing - **not** Open World).
2. "Collect Data" → record (or delete) 50 samples per gesture class.
3. Preprocess collected data to generate additional samples; optional mirror
   option for left-hand support.
4. Train - progress bar until complete.
5. App flags gestures it's uncertain about → review, remove or keep.
6. Model retrains on changes, or finalises if none.
7. Your custom model is saved separately - it does **not** overwrite the
   built-in defaults - and becomes selectable in Settings.

### 06 - Key Bindings
Remap keys for Subway Surfers, Racing, and Open World modes. Select mode tab
→ click binding → press desired key → saved automatically. "RESET TO DEFAULT"
reverts a mode's bindings.

**Default Bindings - Subway Surfers**

| Gesture | Default Key |
|---|---|
| Jump | Up arrow |
| Roll | Down arrow |
| Left | Left arrow |
| Right | Right arrow |
| Space | Space |

**Default Bindings - Racing**

| Gesture | Default Key |
|---|---|
| Accelerate | Up arrow |
| Brake | Down arrow |
| Steer Left | Left arrow |
| Steer Right | Right arrow |
| Horn | H |
| Camera | C |

**Default Bindings - Open World**

| Gesture | Default Key | Gesture | Default Key |
|---|---|---|---|
| Like | Shift | One | 1 |
| Palm | Space | Peace | 2 |
| Thumb Index | Left click | Three | 3 |
| OK | F | Four | 4 |
| Call | R | Peace Inverted | T |
| Dislike | Q | Three-2 | Tab |
| Holy | Esc | Three-3 | G |
| Grip | Alt | Little Finger | Right click |
| | | Grabbing | E |

## Gesture Reference

### General Gestures (active in any mode - app/session control)

| Gesture | Hand Shape | Action |
|---|---|---|
| One Finger | Index raised | Navigate / select zone item 1 |
| Two Fingers | Index + middle | Navigate / select zone item 2 |
| Three Fingers | Three fingers | Navigate / select zone item 3 |
| Pause | Both palms open facing camera | Pause session |
| Continue | Peace sign, both hands | Resume session |
| Game Option 1–4 | Fist + 1/2/3/4 fingers, hold 5s | Switch to Mouse/Subway/Racing/Open World |
| Mouse in Game | Devil horn + index | Open mouse overlay in game mode |
| Exit / Close | Both hands closed to fists (hold) | Close application |

### Mouse Mode Gestures
Cursor mapped from detection zone → full screen via linear interpolation.
Scroll speed is fixed, not proportional to hand speed.

| Gesture | Action |
|---|---|
| Point (raise index) | Move cursor |
| OK sign (pinch, <0.5s) | Single left click |
| OK sign hold (pinch, >0.5s) | Drag (release drops item) |
| Middle pinch (thumb+middle) | Single right-click |
| Three fingers raised | Continuous scroll up |
| Fist | Continuous scroll down |

### Subway Surfers Gestures
Below 75% confidence → treated as idle. 0.3s cooldown between key presses
(Space: 1.0s cooldown). Gesture must change before a new key press fires.

| Gesture | Key Sent |
|---|---|
| Two fingers up | Up arrow (Jump) |
| Two fingers down | Down arrow (Slide) |
| Two fingers left | Left arrow (Swipe left) |
| Two fingers right | Right arrow (Swipe right) |
| Shaka (thumb+pinky) | Space |

### Racing Gestures
Below 60% confidence → ignored. Keys held continuously while gesture is
maintained. Steering uses both hands: angle between left/right wrists -
within ±5° = straight (dead zone); beyond −5° = left held; beyond +5° = right
held.

| Gesture | Key Sent |
|---|---|
| Right thumb up | Up arrow held (Accelerate) |
| Left thumb up | Down arrow held (Brake) |
| Tilt both hands left | Left arrow held |
| Tilt both hands right | Right arrow held |
| Level hands | - (straight) |
| Both thumbs up | Up + Down held simultaneously |
| Left hand index+middle forward | C, tap, 0.4s cooldown (Camera) |
| Right hand index+middle forward | H held (Horn) |

### Open World Gestures
Below 70% confidence → ignored.

| Gesture | Key |
|---|---|
| Two Up (peace up) | W held (Forward) |
| Two Up Inverted | S held (Backward) |
| Three Gun (aim L/R) | A/D (Strafe) |
| Thumbs Up | Shift (Dodge) |
| Open Palm | Space (Jump) |
| Thumb Index (L-sign) | Left click (Ability) |
| OK sign | F (Interact) |
| Call sign | R (Skill) |
| Thumbs Down | Q (Alt Skill) |
| Grip | Alt |
| One/Peace/Three/Four | 1/2/3/4 (Teammate select) |
| Holy (spread hand) | Esc |
| Peace Inverted | T |
| Three-Three | Tab |
| Three-Two | G |
| Grabbing | E |
| Little Finger (pinky up) | Right click |

### Devil Horn Mouse Overlay (all game modes)
Requires "Mouse In Game" toggle enabled in Settings.
- Activate: devil-horn gesture with the hand **opposite** your configured
  mouse side.
- While held: the other hand uses standard Mouse Mode gestures (click, drag,
  scroll).
- Devil-horn hand highlighted orange on camera preview.
- Release the gesture to return to the active game mode.

## Running the Gesture Controller

**Before starting**: camera selected & working, game mode configured, key
bindings set (if non-default), target app/game open and in foreground.

**Start**: Home dashboard → click START → camera captures at 30 FPS, session
starts.

**Pause/exit - 4 ways**:
1. GUI "PAUSE" button.
2. Pause gesture - both palms open; resume via both-peace-signs.
3. Both-fists gesture, held 3 seconds → exits application.
4. Window close button → clean shutdown, waits up to 3s for controller to stop.

**In-session mode switching** (no need to open Settings):

| Switch To | Gesture (hold 5s) |
|---|---|
| Mouse Mode | Fist (one hand) + 1 finger (other hand) |
| Subway Mode | Fist + 2 fingers |
| Racing Mode | Fist + 3 fingers |
| Open World | Fist + 4 fingers |

Countdown shown on camera feed during hold; releasing early cancels.

**Devil Horn overlay**: available any time in Running state while a non-Mouse
mode is active.

## Resetting Your Settings

All your preferences (camera, zone, mode, key bindings, etc.) are saved
automatically as you change them - there's nothing to manually save. If you
want to reset:

1. **Key bindings for one mode**: Key Bindings page (sidebar 06) → "RESET TO
   DEFAULT".
2. **Everything**: delete the app's settings file - the setup flow runs again
   on next launch and every default is restored
   (camera, zone, mode, all of it).

## Troubleshooting

### Camera Not Detected
Symptom: blank preview or "Failed to open camera".

| Cause | Solution |
|---|---|
| Wrong camera index | Settings → Camera selector, try each index (0,1,2...) |
| Camera in use by another app | Close Zoom/Teams/OBS/etc. |
| Permission not granted (macOS) | System Preferences → Privacy & Security → Camera → enable Python/Terminal |
| Virtual camera conflict | Disable virtual cameras (e.g. OBS Virtual Cam) before launch |

### Low Gesture Recognition Accuracy
| Solution | Details |
|---|---|
| Improve lighting | Even, bright frontal lighting; avoid backlighting/colored light |
| Recalibrate distance | Maintain 50–70 cm; delete `app_config.json` to re-trigger setup flow |
| Reduce background clutter | Avoid patterned clothing/busy backgrounds |
| Use a custom model | Train via Train Model page (sidebar 05) |

### Cursor Drift / Out-of-Zone Mapping
| Solution | Details |
|---|---|
| Change zone size | SMALL for large movements; LARGE if too sensitive |
| Switch cursor point | KNUCKLE in Settings for more stability |
| Check reflective surfaces | Mirrors/glasses/jewellery can cause landmark jitter |

### Cursor Seems Frozen / Not Moving
This is expected, not a bug: if your hand leaves the detection zone, or the
app briefly loses track of your hand, the cursor simply stays wherever it
last was - it won't jump or reset. Move your hand back into the detection
zone and it'll pick up tracking again.

### Application Will Not Launch
| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'PySide6'` | `pip install PySide6` |
| `ModuleNotFoundError: No module named 'torch'` | `pip install torch` |
| `RuntimeError: Model file not found` | Verify `logic/data/*.pt` and `*.pkl` exist |
| `ImportError: cannot import name 'HandLandmarker'` | `pip install --upgrade mediapipe` |

### Key Presses Not Registering in Target App
| Cause | Solution |
|---|---|
| Target app not in foreground | Click the game window to focus it before gesturing |
| Wrong key binding | Verify mapping in Key Bindings (sidebar 06) |
| Anti-cheat blocking (Windows) | Kernel-level anti-cheat can block synthetic input - game-side restriction, cannot be bypassed |
| macOS Accessibility permission | System Preferences → Privacy & Security → Accessibility → enable Python/Terminal |

## Known Limitations

- **Theme choice doesn't persist.** Dark/Light mode resets to Light every time
  you restart the app.
- **Open World mode only supports the built-in gesture set.** You can't use a
  custom-trained model for Open World mode yet (custom models work for Mouse,
  Subway Surfers, and Racing).
- **Gesture feedback stays inside the app window.** There's no overlay drawn
  directly on top of your game - you'll see the detected gesture, confidence,
  and status in HANDMOUSE's own window, not layered over the game itself.
