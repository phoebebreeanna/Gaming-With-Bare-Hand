from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget
)
from PySide6.QtCore import Qt


class GameMode(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Game Mode Selection")
        title.setStyleSheet("""
            color: white;
            font-size: 26px;
            font-weight: bold;
        """)
        layout.addWidget(title)

        divider = QWidget()
        divider.setFixedHeight(3)
        divider.setStyleSheet("background-color: #6B35C7;")
        layout.addWidget(divider)

        layout.addSpacing(20)

        #--------------------------Mouse Mode------------------------------------------
        mouse_box = QWidget()
        mouse_box.setFixedHeight(80)
        mouse_box.setStyleSheet("""
            background-color: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
        """)

        #Horizontal layout in the mouse box from left to right
        mouse_layout = QHBoxLayout(mouse_box)
        mouse_layout.setContentsMargins(20, 10,20,10)
        mouse_layout.setSpacing(10)

        mouse_label = QLabel("Mouse Mode")
        mouse_label.setStyleSheet("""
            color: white;
            font-size: 15px;
            background: transparent;
            border: none;
        """)

        #Toggle for mouse mode (on/off)
        self.mouse_toggle = QPushButton("OFF")
        self.mouse_toggle.setFixedSize(70, 35)
        self.mouse_toggle.setCursor(Qt.PointingHandCursor)
        self.mouse_toggle.clicked.connect(self.toggle_mouse)
        self.mouse_enabled = False
        self.update_toggle_style()

        mouse_layout.addWidget(mouse_label)
        mouse_layout.addStretch()
        mouse_layout.addWidget(self.mouse_toggle)

        layout.addWidget(mouse_box)

        #divider line between mouse and game mode
        divider2 = QWidget()
        divider2.setFixedHeight(1)
        divider2.setStyleSheet("background-color: #6B35C7;")
        layout.addWidget(divider2)

        layout.addSpacing(20)

        #--------------------------Game Selection------------------------------------------
        mode_label = QLabel("Select Game Mode")
        mode_label.setStyleSheet("""
            color: white;
            font-size: 18px;
            font-weight: bold;
        """)
        layout.addWidget(mode_label)

        layout.addSpacing(10)

        #Game mode options
        mode_row = QHBoxLayout()
        mode_row.setSpacing(30) #Change spacing between game mode cards

        self.mode_buttons = {}

        modes = [
            ("🚇", "Subway Surfers", "subway",
             "Information here"),
             ("🏎️", "Racing Mode", "racing",
              "Information here"),
             ("⏳", "Coming Soon", "coming", "Information here")
            ]

        self.selected_mode = None

        for icon, name, key, desc in modes:
            choose_btn = self.create_mode_option(icon, name, desc, key)
            self.mode_buttons[key] = choose_btn
            mode_row.addWidget(choose_btn)

        mode_row.addStretch()
        layout.addLayout(mode_row)
        layout.addStretch()

    #--------------------------Mouse Mode------------------------------------------
    def toggle_mouse(self):
        self.mouse_enabled = not self.mouse_enabled
        self.mouse_toggle.setText("ON" if self.mouse_enabled else "OFF")
        self.update_toggle_style()

    def update_toggle_style(self):
        if self.mouse_enabled: #When mouse mode is enable, the container is purple
            self.mouse_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #6B35C7;
                    color: white;
                    font-weight: bold;
                    border-radius: 8px;
                    border: none;
                }
                QPushButton:hover { background-color: #8B55E7; }
            """)
        else: #When mouse mode is disable, the container is transparent with white border
            self.mouse_toggle.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255,255,255,0.15);
                    color: #AAAAAA;
                    font-weight: bold;
                    border-radius: 8px;
                    border: 1px solid rgba(255,255,255,0.2);
                }
                QPushButton:hover { background-color: rgba(255,255,255,0.25); }
            """)

    #--------------------------Game Mode part------------------------------------------
    def create_mode_option(self, icon, name, desc, key):
        gamecard = QPushButton()
        gamecard.setFixedSize(180,160)
        gamecard.setCursor(Qt.PointingHandCursor)
        gamecard.setCheckable(True)
        gamecard.clicked.connect(
            lambda _, k=key: self.select_mode(k)
        )

        #--------------Coming Soon (disabled and greyed out)----------------
        if key == "coming":
            gamecard.setEnabled(False)

        gamecard_layout = QVBoxLayout(gamecard)
        gamecard_layout.setAlignment(Qt.AlignCenter)
        gamecard_layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("""
            font-size: 36px;
            background: transparent;
            border: none;
        """)

        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("""
            color: white;
            font-size: 13px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)

        desc_label = QLabel(desc)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("""
            color: #AAAAAA;
            font-size: 11px;
            background: transparent;
            border: none;
        """)

        gamecard_layout.addWidget(icon_label)
        gamecard_layout.addWidget(name_label)
        gamecard_layout.addWidget(desc_label)

        self.update_card_style(gamecard, False)
        return gamecard

    def select_mode(self, key):
        self.selected_mode = key
        for k, card in self.mode_buttons.items():
            self.update_card_style(card, k == key)

    def update_card_style(self, card, selected):
        if selected:
            card.setStyleSheet("""
                QPushButton {
                    background-color: #6B35C7;
                    border: 2px solid #A78BFA;
                    border-radius: 12px;
                }
            """)
        else:
            card.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255,255,255,0.08);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(107,53,199,0.3);
                    border: 1px solid rgba(255,255,255,0.4);
                }
            """)
