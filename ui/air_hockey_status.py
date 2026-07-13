from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

SKILL_NAMES = {1: "SHIELD", 2: "FREEZE", 3: "DOUBLE PUCK", 4: "SLOW PUCK", 5: "SPEED PUCK"}

class _PlayerColumn(QWidget):
    def __init__(self, title: str):
        super().__init__()
        self.setFixedHeight(52)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 6, 12, 6)
        outer.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.title_lbl = QLabel(title)
        top.addWidget(self.title_lbl)
        self.mover_dot = QLabel("●")
        self.skill_dot = QLabel("●")
        top.addWidget(QLabel("L"))
        top.addWidget(self.mover_dot)
        top.addWidget(QLabel("R"))
        top.addWidget(self.skill_dot)
        top.addStretch()
        outer.addLayout(top)

        self.status_lbl = QLabel("-- · idle")
        self.status_lbl.setWordWrap(False)
        outer.addWidget(self.status_lbl)

    def update_status(self, mover_present, direction, skill_present, skill_count, last_skill):
        self.mover_dot.setStyleSheet(
            f"color: {'#00cc66' if mover_present else '#888888'}; font-size: 9px; background: transparent; border: none;")
        self.skill_dot.setStyleSheet(
            f"color: {'#00cc66' if skill_present else '#888888'}; font-size: 9px; background: transparent; border: none;")

        skill_txt = f"FINGERS {skill_count}" if (skill_present and skill_count) else "--"
        text = f"{direction}  ·  {skill_txt}"
        if last_skill:
            text += f"  ·  LAST: {SKILL_NAMES.get(last_skill, last_skill)}"
        self.status_lbl.setText(text)


class AirHockeyStatusPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.is_dark = False
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.p1 = _PlayerColumn("P1 · WASD")
        self.p2 = _PlayerColumn("P2 · ARROWS")
        self._columns = [self.p1, self.p2]
        row.addWidget(self.p1)
        row.addWidget(self.p2)
        self.apply_theme(False)

    def update_status(self, data: dict):
        self.p1.update_status(
            data.get('p1_mover_present', False), data.get('p1_direction', '--'),
            data.get('p1_skill_present', False), data.get('p1_skill_count', 0),
            data.get('p1_last_skill', 0))
        self.p2.update_status(
            data.get('p2_mover_present', False), data.get('p2_direction', '--'),
            data.get('p2_skill_present', False), data.get('p2_skill_count', 0),
            data.get('p2_last_skill', 0))

    def apply_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if is_dark:
            panel = "#111111"; border = "#262626"; text = "#e8e8e8"; muted = "#6b6b6b"
        else:
            panel = "#F7F3F0"; border = "#D8CEC7"; text = "#111111"; muted = "#8B817B"

        for col in self._columns:
            col.setStyleSheet(f"background-color: {panel}; border: 1px solid {border}; border-radius: 2px;")
            col.title_lbl.setStyleSheet(
                f"font-size: 9px; font-weight: 700; color: {text}; letter-spacing: 1px; background: transparent; border: none;")
            col.status_lbl.setStyleSheet(
                f"font-size: 9px; font-weight: 600; color: {muted}; background: transparent; border: none;")
            for lbl in col.findChildren(QLabel):
                if lbl in (col.mover_dot, col.skill_dot, col.title_lbl, col.status_lbl):
                    continue
                lbl.setStyleSheet(
                    f"font-size: 8px; color: {muted}; background: transparent; border: none;")
