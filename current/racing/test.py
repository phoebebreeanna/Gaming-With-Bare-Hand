import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import torch
import torch.nn as nn
import joblib
import glob
import sys

CONF_THRESHOLD = 0.50


class GestureNet(nn.Module):
    def __init__(self, input_size, num_classes):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 256), nn.BatchNorm1d(256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 128),        nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 64),         nn.BatchNorm1d(64),  nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        return self.net(x)


def normalize(lms):
    coords = np.array([[lm.x, lm.y, lm.z] for lm in lms], dtype=np.float32)
    wx, wy, wz = coords[0]
    coords -= [wx, wy, wz]
    scale = np.sqrt(coords[9, 0]**2 + coords[9, 1]**2)
    scale = max(scale, 1e-6)
    coords /= scale
    return coords.flatten()


def load_model(model_path, le):
    num_classes = len(le.classes_)
    model = GestureNet(126, num_classes)
    model.load_state_dict(torch.load(model_path, map_location='cpu'))
    model.eval()
    return model


def draw_bars(frame, labels, probs, top_label, h, w):
    bar_x     = 10
    bar_y     = h - 30 - len(labels) * 28
    bar_w_max = 220

    for i, (label, prob) in enumerate(zip(labels, probs)):
        y      = bar_y + i * 28
        filled = int(prob * bar_w_max)
        active = label == top_label

        bg_color   = (40, 40, 40)
        fill_color = (0, 220, 100) if active else (80, 120, 200)
        text_color = (255, 255, 255) if active else (160, 160, 160)

        cv2.rectangle(frame, (bar_x, y), (bar_x + bar_w_max, y + 20), bg_color, -1)
        cv2.rectangle(frame, (bar_x, y), (bar_x + filled, y + 20), fill_color, -1)
        cv2.putText(frame, f"{label}  {prob:.0%}",
                    (bar_x + bar_w_max + 8, y + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)


def main():
    model_files = glob.glob('data/*gesture_model.pt') or glob.glob('data/*gesture_model_best.pt')
    le_files    = glob.glob('data/*label_encoder.pkl')

    if not model_files or not le_files:
        print("ERROR: no model / label_encoder found in data/ folder")
        sys.exit(1)

    le    = joblib.load(le_files[0])
    model = load_model(model_files[0], le)
    print(f"Loaded model: {model_files[0]}")
    print(f"Classes: {list(le.classes_)}")

    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options      = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
    detector     = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

    prev_feats = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame    = cv2.flip(frame, 1)
        rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result   = detector.detect(mp_image)
        h, w     = frame.shape[:2]

        if result.hand_landmarks:
            lms    = result.hand_landmarks[0]
            coords = normalize(lms)

            delta      = (coords - prev_feats) if prev_feats is not None else np.zeros(63, dtype=np.float32)
            prev_feats = coords
            feats      = np.concatenate([coords, delta]).astype(np.float32)

            with torch.no_grad():
                logits = model(torch.tensor(feats).unsqueeze(0))
                probs  = torch.softmax(logits, dim=1).squeeze().numpy()

            order     = np.argsort(probs)[::-1]
            top_idx   = order[0]
            top_label = le.classes_[top_idx] if probs[top_idx] >= CONF_THRESHOLD else 'none'
            top_conf  = probs[top_idx]

            sorted_labels = [le.classes_[i] for i in order]
            sorted_probs  = [probs[i] for i in order]

            draw_bars(frame, sorted_labels, sorted_probs, top_label, h, w)

            color = (0, 220, 100) if top_label != 'none' else (0, 80, 255)
            cv2.putText(frame, f"{top_label}  {top_conf:.0%}",
                        (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 2)

            pts = [(int(lm.x * w), int(lm.y * h)) for lm in lms]
            connections = [
                (0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
                (0,9),(9,10),(10,11),(11,12),(0,13),(13,14),(14,15),(15,16),
                (0,17),(17,18),(18,19),(19,20),(5,9),(9,13),(13,17),
            ]
            for a, b in connections:
                cv2.line(frame, pts[a], pts[b], (0, 200, 255), 1, cv2.LINE_AA)
            for i, (px, py) in enumerate(pts):
                r = 5 if i in {4, 8, 12, 16, 20} else 3
                cv2.circle(frame, (px, py), r, (255, 255, 255), -1, cv2.LINE_AA)

        else:
            prev_feats = None
            cv2.putText(frame, "no hand", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 80, 255), 2)

        cv2.putText(frame, "ESC to quit", (w - 120, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 100, 100), 1)
        cv2.imshow('Gesture Test', frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    detector.close()


if __name__ == '__main__':
    main()
