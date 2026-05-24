import math
import torch
import torch.nn as nn

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

def extract_features(lms, prev_row):
    wx, wy, wz = lms[0].x, lms[0].y, lms[0].z
    scale = max(math.sqrt((lms[9].x - wx)**2 + (lms[9].y - wy)**2 + (lms[9].z - wz)**2), 1e-6)
    row = []
    for lm in lms:
        row.extend([(lm.x - wx) / scale, (lm.y - wy) / scale, (lm.z - wz) / scale])
    delta = [c - p for c, p in zip(row, prev_row)] if prev_row else [0.0] * 63
    return row + delta, row

def run_nn(lms, prev_row, model, le, conf_thresh):
    if model is None or le is None:
        return 'none', 0.0, prev_row
    features, new_prev = extract_features(lms, prev_row)
    x = torch.tensor([features], dtype=torch.float32)
    with torch.no_grad():
        probs = torch.softmax(model(x), dim=1)[0]
        conf, idx = probs.max(0)
    if conf.item() < conf_thresh:
        return 'none', conf.item(), new_prev
    return le.inverse_transform([idx.item()])[0], conf.item(), new_prev

def load_nn(weights_path, encoder_path, input_size=126, tag='model'):
    try:
        import joblib
        le = joblib.load(encoder_path)
        net = GestureNet(input_size, len(le.classes_))
        net.load_state_dict(torch.load(weights_path, map_location='cpu', weights_only=False))
        net.eval()
        print(f"[NN:{tag}] Loaded - classes: {list(le.classes_)}")
        return net, le
    except FileNotFoundError:
        print(f"[NN:{tag}] Model not found: {weights_path}")
        return None, None
    except Exception as e:
        print(f"[NN:{tag}] Load error: {e}")
        return None, None

