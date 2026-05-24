import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QApplication, QComboBox,
    QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QTimer, QEvent
from PySide6.QtGui import QPixmap

from ui.user_guide import UserGuide
from ui.gesture_guide import GestureGuide
from ui.game_mode import GameMode
from ui.pipeline_ui import PipelineUI
from ui.mainmenu_setup import MainMenuSetup
from ui.mainmenu_calibration import MainMenuCalibration
from ui.mainmenu_zone import MainMenuZone

from logic.hand_controller import HandControllerThread, CameraPreviewThread, list_cameras
from logic.app_config import is_setup_done, get_saved_zone, mark_setup_done

class MainMenu(QWidget):
    def __init__(self):
        super().__init__()
        self.is_dark = False
        self.controller = None
        self._preview_thread = None
        self._is_running = False
        self._is_paused = False
        self._last_camera_pixmap = None
        self._optimal_since = None
        self._zone_hold_since = None
        self._zone_pending = None
        self.start_time = time.time() 
        self.init_ui()

        if not is_setup_done():
            self.home_stack.setCurrentIndex(1)

        self.uptime_timer = QTimer()
        self.uptime_timer.timeout.connect(self.update_uptime)
        self.uptime_timer.start(1000)

        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.update_clock()

    def init_ui(self):
        self.setAutoFillBackground(True)
        self.setStyleSheet("""
            MainMenu {
                background-color: #F4F4F4;
            }
            MainMenu QLabel {
                background: transparent;
                color: #7A706C;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.setStyleSheet("background: transparent;")
        main_layout.addWidget(self.pages)

        self.pages.addWidget(self.create_home_page())

        self.user_guide = UserGuide()
        self.user_guide.on_menu_toggle.connect(self.toggle_sidebar)
        self.pages.addWidget(self.user_guide)

        self.gesture_guide = GestureGuide()
        self.gesture_guide.on_menu_toggle.connect(self.toggle_sidebar)
        self.pages.addWidget(self.gesture_guide)

        self.pages.addWidget(GameMode())

        self.pipeline_ui = PipelineUI(is_dark=self.is_dark)
        self.pipeline_ui.on_menu_toggle.connect(self.toggle_sidebar)
        self.pages.addWidget(self.pipeline_ui)

        self.pages.setCurrentIndex(0)

    def create_sidebar(self):
        self.sidebar = sidebar = QWidget()
        sidebar.setFixedWidth(222)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #ECECEC;
                border-radius: 0px;
            }

            QPushButton {
                background-color: transparent;
                color: #1A1A1A;
                font-size: 11px;
                letter-spacing: 1.2px;
                text-align: left;
                padding: 13px 14px;
                border: none;
                border-radius: 0px;
            }

            QPushButton:hover {
                background-color: #E4E4E4;
                color: #000000;
            }

            QPushButton:checked {
                background-color: #F6F6F6;
                color: #000000;
                font-weight: 700;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(0)
        self.sidebar_dividers = []

        self.logo_box = QWidget()
        self.logo_box.setStyleSheet("""
            background: transparent;
            border: none;
            border-radius: 0px;
        """)

        ll = QHBoxLayout(self.logo_box)
        ll.setContentsMargins(8, 0, 8, 14)
        ll.setSpacing(10)

        logo_text = QWidget()
        logo_text.setStyleSheet("background: transparent; border: none;")
        logo_text_layout = QVBoxLayout(logo_text)
        logo_text_layout.setContentsMargins(0, 0, 0, 0)
        logo_text_layout.setSpacing(3)

        self.logo_name_lbl = QLabel("HANDMOUSE")
        self.logo_name_lbl.setAlignment(Qt.AlignLeft)
        self.logo_name_lbl.setStyleSheet(
             "font-size: 11px; font-weight: 800; color: #111111; letter-spacing: 1.5px; background: transparent; border: none;")

        self.logo_sub = QLabel("Gesture Control · v1.0")
        self.logo_sub.setAlignment(Qt.AlignLeft)
        self.logo_sub.setStyleSheet(
             "font-size: 8px; color: #7E8A9A; letter-spacing: 1px; background: transparent; border: none;")
        logo_text_layout.addWidget(self.logo_name_lbl)
        logo_text_layout.addWidget(self.logo_sub)
        ll.addWidget(logo_text)
        ll.addStretch()
        layout.addWidget(self.logo_box)

        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #D4D4D4;")
        self.sidebar_dividers.append(line)
        layout.addWidget(line)
        layout.addSpacing(10)

        self.nav_buttons = []

        self.menu_lbl = QLabel("MENU")
        self.menu_lbl.setContentsMargins(6, 10, 0, 6)
        self.menu_lbl.setStyleSheet(
            "font-size: 8px; color: #9AA0A6; font-weight: bold;"
            "letter-spacing: 1.2px; background: transparent; border: none;")
        layout.addWidget(self.menu_lbl)

        for label, index in [
            ("01      -     HOME", 0),
            ("02      -     USER GUIDE", 1),
            ("03      -     GESTURE GUIDE", 2),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        layout.addSpacing(4)

        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #D4D4D4;")
        self.sidebar_dividers.append(line)
        layout.addWidget(line)

        self.setup_lbl = QLabel("SETUP")
        self.setup_lbl.setContentsMargins(6, 12, 0, 6)
        self.setup_lbl.setStyleSheet(
            "font-size: 8px; color: #9AA0A6; font-weight: bold;"
            "letter-spacing: 1.2px; background: transparent; border: none;")
        layout.addWidget(self.setup_lbl)

        for label, index in [
            ("04      -     GAME OPTION", 3),
            ("05      -     TRAIN MODEL", 4),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        self.nav_buttons[0].setChecked(True)
        layout.addStretch()

        self.theme_btn = QPushButton("DARK MODE")
        self.theme_btn.setFixedWidth(132)
        self.theme_btn.setFixedHeight(30)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #000000;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1.5px;
                text-align: center;
                padding: 2px 8px;
            }
            QPushButton:hover { background: #EFEFEF; }
        """)
        self.theme_btn.clicked.connect(self.toggle_theme)
        theme_row = QHBoxLayout()
        theme_row.setContentsMargins(8, 0, 8, 0)
        theme_row.addStretch()
        theme_row.addWidget(self.theme_btn)
        theme_row.addStretch()
        layout.addLayout(theme_row)

        self.version_lbl = QLabel(" v1.0")
        self.version_lbl.setAlignment(Qt.AlignCenter)
        self.version_lbl.setStyleSheet(
            "font-size: 9px; color: #C7C0BC; background: transparent; border: none;")
        layout.addWidget(self.version_lbl)

        return sidebar

    def create_home_page(self):
        page = QWidget()
        self.home_page = page
        page.setStyleSheet("background-color: #F4F4F4;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.home_stack = QStackedWidget()
        layout.addWidget(self.home_stack)

        self.home_stack.addWidget(self.create_home_dashboard())

        self.setup_guide = MainMenuSetup(is_dark=self.is_dark)
        self.setup_guide.on_lets_go.connect(self._on_setup_lets_go)
        self.setup_guide.on_menu_toggle.connect(self.toggle_sidebar)
        self.home_stack.addWidget(self.setup_guide) 

        self.calibration_guide = MainMenuCalibration(is_dark=self.is_dark)
        self.calibration_guide.on_continue.connect(self._on_distance_continue)
        self.calibration_guide.on_back.connect(self._on_distance_back)
        self.calibration_guide.on_menu_toggle.connect(self.toggle_sidebar)
        self.home_stack.addWidget(self.calibration_guide) 

        self.zone_guide = MainMenuZone(is_dark=self.is_dark)
        self.zone_guide.on_zone_continue.connect(self._on_zone_continue)
        self.zone_guide.on_zone_back.connect(self._on_zone_back)
        self.zone_guide.on_menu_toggle.connect(self.toggle_sidebar)
        self.home_stack.addWidget(self.zone_guide) 

        return page

    def create_home_dashboard(self):
        page = QWidget()
        self.home_dashboard_page = page
        page.setStyleSheet("background-color: #F4F4F4;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.menu_toggle_btn = QPushButton("☰")
        self.menu_toggle_btn.setFixedSize(36, 42)
        self.menu_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.menu_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #1A1A2E;
                font-size: 18px;
                border: none;
                border-radius: 2px;
            }

            QPushButton:hover {
                background-color: #EDE5DF;
            }
        """)
        self.menu_toggle_btn.clicked.connect(self.toggle_sidebar)
        top_row.addWidget(self.menu_toggle_btn)

        self.home_brand = QWidget()
        self.home_brand.setFixedHeight(42)
        brand_layout = QHBoxLayout(self.home_brand)
        brand_layout.setContentsMargins(14, 0, 18, 0)
        brand_layout.setSpacing(10)
        self.home_title = QLabel("HANDMOUSE")
        self.home_version = QLabel("v1.0")
        brand_layout.addWidget(self.home_title)
        brand_layout.addWidget(self.home_version)
        top_row.addWidget(self.home_brand)
        self.home_brand.setStyleSheet("background: transparent; border-left: 1px solid #D8CEC7; border-right: 1px solid #D8CEC7;")
        self.home_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #111111; letter-spacing: 1.5px; background: transparent; border: none;")
        self.home_version.setStyleSheet("font-size: 8px; color: #7E8A9A; letter-spacing: 1px; background: transparent; border: none;")

        top_row.addStretch()

        self.top_info = QWidget()
        self.top_info.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        top_info_layout = QHBoxLayout(self.top_info)
        top_info_layout.setContentsMargins(0, 0, 0, 0)
        top_info_layout.setSpacing(0)

        def make_top_label(text):
            lbl = QLabel(text)
            lbl.setFixedHeight(42)
            lbl.setStyleSheet("""
                QLabel {
                    color: #6F655F;
                    font-size: 9px;
                    letter-spacing: 1.2px;
                    padding: 0 18px;
                    border-left: 1px solid #D8CEC7;
                    background: transparent;
                }
            """)
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        self.top_ready_lbl = make_top_label("● READY")
        self.top_ready_lbl.setStyleSheet("""
            QLabel {
                color: #B86A54;
                font-size: 9px;
                letter-spacing: 1.2px;
                padding: 0 18px;
                border-left: 1px solid #D8CEC7;
                background: transparent;
            }
        """)

        self.top_time_lbl = make_top_label("")

        top_info_layout.addWidget(self.top_ready_lbl)
        top_info_layout.addWidget(self.top_time_lbl)

        top_row.addWidget(self.top_info)

        self.camera_combo = QComboBox()
        self.camera_combo.hide()
        self._refresh_cameras()
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)

        layout.addLayout(top_row)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.info_cards = {}
        self.info_card_widgets = {}
        self.info_header_labels = {}
        for lbl, val in [
            ("GESTURE", "IDLE"),
            ("ACTION", "None"),
            ("MODE", "MOUSE"),
            ("STATUS", "Press Start"),
        ]:
            card = QWidget()
            card.setFixedHeight(52)
            card.setStyleSheet("""
                background-color: #F7F3F0;
                border: 1px solid #D8CEC7;
                border-radius: 2px;
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 7, 12, 7)
            cl.setSpacing(2)
            h = QLabel(lbl)
            h.setStyleSheet("""
                font-size: 8px;
                color: #8B817B;
                letter-spacing: 1.5px;
                background: transparent;
                border: none;
            """)
            cl.addWidget(h)
            v = QLabel(val)
            v.setStyleSheet("""
                font-size: 11px;
                font-weight: 700;
                color: #111111;
                background: transparent;
                border: none;
            """)
            cl.addWidget(v)
            self.info_header_labels[lbl] = h
            self.info_cards[lbl] = v
            self.info_card_widgets[lbl] = card
            top_row.addWidget(card)
        layout.addLayout(top_row)

        self.camera_frame = QWidget()
        self.camera_frame.setStyleSheet("""
            background-color: #000000;
            border: 1px solid #D8D8D8;
            border-radius: 4px;
        """)

        camera_layout = QVBoxLayout(self.camera_frame)
        camera_layout.setContentsMargins(10, 8, 10, 8)
        camera_layout.setSpacing(0)

        camera_top = QHBoxLayout()

        self.rec_lbl = QLabel("● REC  ·  00:00:00")
        self.rec_lbl.setStyleSheet("""
            color: #B86A54;
            font-size: 8px;
            letter-spacing: 1.2px;
            background: transparent;
            border: none;
        """)

        camera_top.addWidget(self.rec_lbl)
        camera_top.addStretch()
        camera_layout.addLayout(camera_top)

        self.camera_label = QLabel("LIVE CAMERA FEED")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(0, 0)
        self.camera_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.camera_label.installEventFilter(self)
        self.camera_label.setStyleSheet("""
            background: transparent;
            color: #C9C9C9;
            font-size: 10px;
            letter-spacing: 2px;
            border: none;
        """)
        camera_layout.addWidget(self.camera_label, stretch=1)

        self.hold_bar_widget = QWidget()
        self.hold_bar_widget.setFixedHeight(26)
        hb_inner = QHBoxLayout(self.hold_bar_widget)
        hb_inner.setContentsMargins(0, 4, 0, 4)
        hb_inner.setSpacing(8)

        self.hold_bar_label = QLabel("ACTION")
        self.hold_bar_label.setFixedWidth(140)
        self.hold_bar_label.setStyleSheet(
            "color:#6F655F;font-size:8px;font-weight:700;letter-spacing:1.4px;"
            "background:transparent;border:none;")

        self.hold_bar_bg = QWidget()
        self.hold_bar_bg.setFixedHeight(4)
        self.hold_bar_bg.setStyleSheet(
            "background-color:#E8E0DA;border-radius:2px;border:none;")
        self.hold_bar_fill = QWidget(self.hold_bar_bg)
        self.hold_bar_fill.setGeometry(0, 0, 0, 4)
        self.hold_bar_fill.setStyleSheet(
            "background-color:#1A1A1A;border-radius:2px;border:none;")

        hb_inner.addWidget(self.hold_bar_label)
        hb_inner.addWidget(self.hold_bar_bg, stretch=1)
        layout.addWidget(self.hold_bar_widget)

        layout.addWidget(self.camera_frame, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.footer_status = QLabel(
            "ZONE · MEDIUM    UPTIME · 00:00:00"
        )

        self.footer_status.setStyleSheet("""
            color: #6F655F;
            font-size: 8px;
            font-weight: 600;
            letter-spacing: 1.5px;
            background: transparent;
            border: none;
        """)
        self.footer_status.setMinimumWidth(160)
        self.footer_status.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        btn_row.addWidget(self.footer_status)
        btn_row.addStretch()

        self.start_btn = QPushButton("Start")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #1A1A1A;
                color: white;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                border: 1px solid #2A2A2A;
                border-radius: 2px;
                padding: 8px 20px;
                min-width: 64px;
            }

            QPushButton:hover {
                background-color: #2A2A2A;
            }
        """)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #F7F3F0;
                color: #8B5E00;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                border: 1px solid #D6CCC5;
                border-radius: 2px;
                padding: 8px 20px;
                min-width: 64px;
            }

            QPushButton:hover {
                background-color: #EFE7E1;
            }
        """)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #F7F3F0;
                color: #555555;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                border: 1px solid #D6CCC5;
                border-radius: 2px;
                padding: 8px 20px;
                min-width: 64px;
            }

            QPushButton:hover {
                background-color: #EFE7E1;
            }
        """)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #F7F3F0;
                color: #B44545;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                border: 1px solid #E2B8B8;
                border-radius: 2px;
                padding: 8px 20px;
                min-width: 64px;
            }

            QPushButton:hover {
                background-color: #F4E6E6;
            }
        """)
        self.start_btn.clicked.connect(self._on_start)   
        self.pause_btn.clicked.connect(self._on_pause)   
        self.stop_btn.clicked.connect(self._on_stop)
        self.exit_btn.clicked.connect(QApplication.quit)

        self.footer_buttons = [self.start_btn, self.pause_btn, self.stop_btn, self.exit_btn]
        for btn in self.footer_buttons:
            btn.setFixedWidth(84)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.exit_btn)
        layout.addLayout(btn_row)

        return page

    def switch_page(self, index):
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def toggle_sidebar(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())
        QTimer.singleShot(0, self._rescale_camera_frame)
        QTimer.singleShot(80, self._rescale_camera_frame)

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        if self.is_dark:

            win = self.window()
            if win:
                win.setStyleSheet("QMainWindow { background-color: #0a0a0a; }")
            self.setStyleSheet("""
                MainMenu { background: #0a0a0a; }
                MainMenu QLabel { background: transparent; color: #e8e8e8; }
            """)
            self.home_page.setStyleSheet("background-color: #0a0a0a;")
            self.home_dashboard_page.setStyleSheet("background-color: #0a0a0a;")
            self.theme_btn.setText("LIGHT MODE")
            self.theme_btn.setStyleSheet("""
                QPushButton {
                    background: #111111;
                    color: #9a9a9a;
                    border: 1px solid #262626;
                    border-radius: 4px;
                    font-size: 9px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    text-align: center;
                    padding: 2px 8px;
                }
                QPushButton:hover { background: #161616; color: #e8e8e8; }
            """)
            self.logo_box.setStyleSheet("""
                background: transparent;
                border: none;
                border-radius: 0px;
            """)
            self.logo_name_lbl.setStyleSheet(
                "font-size:11px;font-weight:800;color:#e8e8e8;letter-spacing:1.5px;background:transparent;border:none;")
            self.logo_sub.setStyleSheet(
                "font-size:8px;color:#6b6b6b;letter-spacing:1px;background:transparent;border:none;")
            self.menu_lbl.setStyleSheet(
                "font-size:8px;color:#9a9a9a;font-weight:bold;letter-spacing:1.2px;"
                "background:transparent;border:none;")
            self.setup_lbl.setStyleSheet(
                "font-size:8px;color:#9a9a9a;font-weight:bold;letter-spacing:1.2px;"
                "background:transparent;border:none;")
            self.version_lbl.setStyleSheet(
                "font-size:9px;color:#6b6b6b;background:transparent;border:none;")
            self.sidebar.setStyleSheet("""
                QWidget {
                    background-color: #111111;
                    border-radius: 0px;
                    border: 1px solid #262626;
                }
                QPushButton {
                    background-color: transparent;
                    color: #9a9a9a;
                    font-size: 11px;
                    letter-spacing: 1.2px;
                    text-align: left;
                    padding: 13px 14px;
                    border: none;
                    border-radius: 0px;
                }
                QPushButton:hover {
                    background-color: #161616;
                    color: #e8e8e8;
                }
                QPushButton:checked {
                    background-color: #050505;
                    color: #e8e8e8;
                    font-weight: 700;
                }
            """)
            for divider in self.sidebar_dividers:
                divider.setStyleSheet("background-color: #262626; border: none;")
            self.home_title.setStyleSheet("""
                font-size: 11px;
                font-weight: 800;
                color: #e8e8e8;
                letter-spacing: 1.5px;
                background: transparent;
                border: none;
            """)
            self.home_version.setStyleSheet("""
                font-size: 8px;
                color: #6b6b6b;
                letter-spacing: 1px;
                background: transparent;
                border: none;
            """)
            self.home_brand.setStyleSheet("background: transparent; border-left: 1px solid #262626; border-right: 1px solid #262626;")
            self.menu_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #9a9a9a;
                    font-size: 18px;
                    border: none;
                    border-radius: 2px;
                }

                QPushButton:hover {
                    background-color: #161616;
                    color: #e8e8e8;
                }
            """)
            self.top_ready_lbl.setStyleSheet("""
                QLabel {
                    color: #e8e8e8;
                    font-size: 9px;
                    letter-spacing: 1.2px;
                    padding: 0 18px;
                    border-left: 1px solid #262626;
                    background: transparent;
                }
            """)
            self.top_time_lbl.setStyleSheet("""
                QLabel {
                    color: #9a9a9a;
                    font-size: 9px;
                    letter-spacing: 1.2px;
                    padding: 0 18px;
                    border-left: 1px solid #262626;
                    background: transparent;
                }
            """)
            self.camera_label.setStyleSheet("""
                background: transparent;
                color: #262626;
                font-size: 10px;
                letter-spacing: 2px;
                border: none;
            """)
            self.camera_frame.setStyleSheet("""
                background-color: #000000;
                border: 1px solid #262626;
                border-radius: 4px;
            """)
            self.camera_combo.setStyleSheet("""
                QComboBox {
                    background: #111111; color: #9a9a9a;
                    border: 1px solid #262626;
                    border-radius: 8px; padding: 4px 8px; font-size: 12px;
                }
                QComboBox::drop-down { border: none; width: 20px; }
                QComboBox::down-arrow {
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid #9a9a9a;
                    width: 0; height: 0; margin-right: 6px;
                }
                QComboBox QAbstractItemView {
                    background: #111111; color: #e8e8e8;
                    border: 1px solid #262626;
                    selection-background-color: #161616;
                    selection-color: #e8e8e8; outline: none;
                }
            """)
            for key in self.info_cards:
                self.info_card_widgets[key].setStyleSheet("""
                    background-color: #111111;
                    border: 1px solid #262626;
                    border-radius: 2px;
                """)
                self.info_header_labels[key].setStyleSheet("""
                    font-size: 8px;
                    color: #6b6b6b;
                    letter-spacing: 1.5px;
                    background: transparent;
                    border: none;
                """)
                self.info_cards[key].setStyleSheet("""
                    font-size: 11px;
                    font-weight: 700;
                    color: #e8e8e8;
                    background: transparent;
                    border: none;
                """)
            self.rec_lbl.setStyleSheet("""
                color: #e8e8e8;
                font-size: 8px;
                letter-spacing: 1.2px;
                background: transparent;
                border: none;
            """)
            self.footer_status.setStyleSheet("""
                color: #6b6b6b;
                font-size: 8px;
                font-weight: 600;
                letter-spacing: 1.5px;
                background: transparent;
                border: none;
            """)
            self.hold_bar_label.setStyleSheet(
                "color:#6b6b6b;font-size:8px;font-weight:700;letter-spacing:1.4px;"
                "background:transparent;border:none;")
            self.hold_bar_bg.setStyleSheet(
                "background-color:#262626;border-radius:2px;border:none;")
            self.hold_bar_fill.setStyleSheet(
                "background-color:#e8e8e8;border-radius:2px;border:none;")

            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e8e8e8;
                    color: #111111;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    border: 1px solid #e8e8e8;
                    border-radius: 2px;
                    padding: 8px 20px;
                    min-width: 64px;
                }
                QPushButton:hover { background-color: #ffffff; }
                QPushButton:disabled {
                    background-color: #262626;
                    color: #6b6b6b;
                    border-color: #262626;
                }
            """)
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #111111;
                    color: #9a9a9a;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    border: 1px solid #262626;
                    border-radius: 2px;
                    padding: 8px 20px;
                    min-width: 64px;
                }
                QPushButton:hover {
                    background-color: #161616;
                    color: #e8e8e8;
                }
                QPushButton:disabled {
                    background-color: #111111;
                    color: #6b6b6b;
                    border-color: #262626;
                }
            """)
            self.stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #111111;
                    color: #9a9a9a;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    border: 1px solid #262626;
                    border-radius: 2px;
                    padding: 8px 20px;
                    min-width: 64px;
                }
                QPushButton:hover {
                    background-color: #161616;
                    color: #e8e8e8;
                }
                QPushButton:disabled {
                    background-color: #111111;
                    color: #6b6b6b;
                    border-color: #262626;
                }
            """)
            self.exit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #111111;
                    color: #9a9a9a;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    border: 1px solid #262626;
                    border-radius: 2px;
                    padding: 8px 20px;
                    min-width: 64px;
                }
                QPushButton:hover {
                    background-color: #161616;
                    color: #e8e8e8;
                }
            """)
        else:
            win = self.window()
            if win:
                win.setStyleSheet("""
                    QMainWindow { background-color: #F4F4F4; }
                """)
            self.setStyleSheet("""
                MainMenu { background-color: #F4F4F4; }
                MainMenu QLabel { background: transparent; color: #7A706C; }
            """)
            self.home_page.setStyleSheet("background-color: #F4F4F4;")
            self.home_dashboard_page.setStyleSheet("background-color: #F4F4F4;")
            self.theme_btn.setText("DARK MODE")
            self.theme_btn.setStyleSheet("""
                QPushButton {
                    background: white;
                    color: #000000;
                    border: 1px solid #BDBDBD;
                    border-radius: 4px;
                    font-size: 9px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    text-align: center;
                    padding: 2px 8px;
                }
                QPushButton:hover { background: #EFEFEF; }
            """)
            self.logo_box.setStyleSheet("""
                background: transparent;
                border: none;
                border-radius: 0px;
            """)
            self.logo_name_lbl.setStyleSheet(
                "font-size:11px;font-weight:800;color:#111111;letter-spacing:1.5px;background:transparent;border:none;")
            self.logo_sub.setStyleSheet(
                "font-size:8px;color:#7E8A9A;letter-spacing:1px;background:transparent;border:none;")
            self.home_title.setStyleSheet("""
                font-size: 11px;
                font-weight: 800;
                color: #111111;
                letter-spacing: 1.5px;
                background: transparent;
                border: none;
            """)
            self.home_version.setStyleSheet("""
                font-size: 8px;
                color: #7E8A9A;
                letter-spacing: 1px;
                background: transparent;
                border: none;
            """)
            self.home_brand.setStyleSheet("background: transparent; border-left: 1px solid #D8CEC7; border-right: 1px solid #D8CEC7;")
            self.menu_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #1A1A2E;
                    font-size: 18px;
                    border: none;
                    border-radius: 2px;
                }

                QPushButton:hover {
                    background-color: #EDE5DF;
                }
            """)
            self.top_ready_lbl.setStyleSheet("""
                QLabel {
                    color: #B86A54;
                    font-size: 9px;
                    letter-spacing: 1.2px;
                    padding: 0 18px;
                    border-left: 1px solid #D8CEC7;
                    background: transparent;
                }
            """)
            self.top_time_lbl.setStyleSheet("""
                QLabel {
                    color: #6F655F;
                    font-size: 9px;
                    letter-spacing: 1.2px;
                    padding: 0 18px;
                    border-left: 1px solid #D8CEC7;
                    background: transparent;
                }
            """)
            self.menu_lbl.setStyleSheet(
                "font-size:8px;color:#9AA0A6;font-weight:bold;letter-spacing:1.2px;"
                "background:transparent;border:none;")
            self.setup_lbl.setStyleSheet(
                "font-size:8px;color:#9AA0A6;font-weight:bold;letter-spacing:1.2px;"
                "background:transparent;border:none;")
            self.version_lbl.setStyleSheet(
                "font-size:9px;color:#C7C0BC;background:transparent;border:none;")
            self.sidebar.setStyleSheet("""
                QWidget {
                    background-color: #ECECEC;
                    border-radius: 0px;
                }

                QPushButton {
                    background-color: transparent;
                    color: #1A1A1A;
                    font-size: 11px;
                    letter-spacing: 1.2px;
                    text-align: left;
                    padding: 13px 14px;
                    border: none;
                    border-radius: 0px;
                }

                QPushButton:hover {
                    background-color: #E4E4E4;
                    color: #000000;
                }

                QPushButton:checked {
                    background-color: #F6F6F6;
                    color: #000000;
                    font-weight: 700;
                }
            """)
            for divider in self.sidebar_dividers:
                divider.setStyleSheet("background-color: #D4D4D4; border: none;")
            self.camera_label.setStyleSheet("""
                background: transparent; color: #C9C9C9;
                font-size: 10px; letter-spacing: 2px; border: none;
            """)
            self.camera_frame.setStyleSheet("""
                background-color: #000000;
                border: 1px solid #D8D8D8;
                border-radius: 4px;
            """)
            self.rec_lbl.setStyleSheet("""
                color: #B86A54;
                font-size: 8px;
                letter-spacing: 1.2px;
                background: transparent;
                border: none;
            """)
            self.footer_status.setStyleSheet("""
                color: #6F655F;
                font-size: 8px;
                font-weight: 600;
                letter-spacing: 1.5px;
                background: transparent;
                border: none;
            """)
            self.camera_combo.setStyleSheet("""
                QComboBox {
                    background: #F7F3F0; color: #1F2937;
                    border: 1px solid #D6D3D1;
                    border-radius: 8px; padding: 4px 8px; font-size: 12px;
                }
                QComboBox::drop-down { border: none; width: 20px; }
                QComboBox::down-arrow {
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid #6B7280;
                    width: 0; height: 0; margin-right: 6px;
                }
                QComboBox QAbstractItemView {
                    background: #F7F3F0; color: #1F2937;
                    border: 1px solid #D6D3D1;
                    selection-background-color: #E7E5E4;
                    selection-color: #111827; outline: none;
                }
            """)
            for key in [
                ("GESTURE"),
                ("ACTION"),
                ("MODE"),
                ("STATUS"),
            ]:
                self.info_card_widgets[key].setStyleSheet("""
                    background-color: #F7F3F0;
                    border: 1px solid #D8CEC7;
                    border-radius: 2px;
                """)
                self.info_header_labels[key].setStyleSheet("""
                    font-size: 8px;
                    color: #8B817B;
                    letter-spacing: 1.5px;
                    background: transparent;
                    border: none;
                """)
                self.info_cards[key].setStyleSheet("""
                    font-size: 11px;
                    font-weight: 700;
                    color: #111111;
                    background: transparent;
                    border: none;
                """)
            self.hold_bar_label.setStyleSheet(
                "color:#6F655F;font-size:8px;font-weight:700;letter-spacing:1.4px;"
                "background:transparent;border:none;")
            self.hold_bar_bg.setStyleSheet(
                "background-color:#E8E0DA;border-radius:2px;border:none;")
            self.hold_bar_fill.setStyleSheet(
                "background-color:#1A1A1A;border-radius:2px;border:none;")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1A1A1A;
                    color: white;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    border: 1px solid #2A2A2A;
                    border-radius: 2px;
                    padding: 8px 20px;
                    min-width: 64px;
                }

                QPushButton:hover {
                    background-color: #2A2A2A;
                }
            """)
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F7F3F0;
                    color: #8B5E00;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    border: 1px solid #D6CCC5;
                    border-radius: 2px;
                    padding: 8px 20px;
                    min-width: 64px;
                }

                QPushButton:hover {
                    background-color: #EFE7E1;
                }
            """)
            self.stop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F7F3F0;
                    color: #555555;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    border: 1px solid #D6CCC5;
                    border-radius: 2px;
                    padding: 8px 20px;
                    min-width: 64px;
                }

                QPushButton:hover {
                    background-color: #EFE7E1;
                }
            """)
            self.exit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F7F3F0;
                    color: #B44545;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    border: 1px solid #E2B8B8;
                    border-radius: 2px;
                    padding: 8px 20px;
                    min-width: 64px;
                }

                QPushButton:hover {
                    background-color: #F4E6E6;
                }
            """)

        self.setup_guide.apply_theme(self.is_dark)
        self.calibration_guide.apply_theme(self.is_dark)
        self.zone_guide.apply_theme(self.is_dark)
        self.user_guide.apply_theme(self.is_dark)
        self.gesture_guide.apply_theme(self.is_dark)
        self.pipeline_ui.apply_theme(self.is_dark)
        self.update()
        self.repaint()

    def _refresh_cameras(self):
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        cameras = list_cameras()
        if not cameras:
            self.camera_combo.addItem("No camera found", -1)
        else:
            for idx in cameras:
                self.camera_combo.addItem(
                    f"Camera {idx}" + (" (Default)" if idx == 0 else ""), idx)
        self.camera_combo.blockSignals(False)

    def _on_camera_changed(self, combo_idx: int):
        if not self._is_running: return
        cam = self.camera_combo.itemData(combo_idx)
        if cam is not None and cam >= 0 and self.controller:
            self.controller.set_camera(cam)

    def _get_selected_camera(self) -> int:
        d = self.camera_combo.itemData(self.camera_combo.currentIndex())
        return d if d is not None else 0

    def update_uptime(self):
        elapsed = int(time.time() - self.start_time)

        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        uptime = f"{hours:02}:{minutes:02}:{seconds:02}"

        if hasattr(self, "footer_status"):
            self.footer_status.setText(
                f"ZONE · MEDIUM    UPTIME · {uptime}"
            )
        if hasattr(self, "rec_lbl"):
            self.rec_lbl.setText(f"● REC  ·  {uptime}")

    def update_clock(self):
        current_time = time.strftime("%H:%M:%S")
        self.top_time_lbl.setText(current_time)

    def _on_start(self):
        if self._is_paused and self.controller:
            self.controller.resume()
            self._is_paused = False
            self.start_btn.setText("Start")
            self.pause_btn.setText("Pause")
            return
        if self._is_running:
            return
        if is_setup_done():
            self._start_controller()
        else:
            self.home_stack.setCurrentIndex(1)

    def _on_setup_lets_go(self):
        self.home_stack.setCurrentIndex(2)
        self._start_preview()

    def _on_distance_continue(self):
        self.home_stack.setCurrentIndex(3)

    def _on_distance_back(self):
        self._optimal_since = None
        self._stop_preview()
        self.home_stack.setCurrentIndex(1)

    def _on_zone_back(self):
        self._zone_hold_since = None
        self._zone_pending = None
        self.home_stack.setCurrentIndex(2)

    def _on_zone_continue(self):
        self._zone_hold_since = None
        self._zone_pending = None
        zone = getattr(self.zone_guide, 'selected_zone', 'medium')
        mark_setup_done(zone)
        self._stop_preview()
        self.home_stack.setCurrentIndex(0)
        self._start_controller()

    def _start_preview(self):
        if self._preview_thread and self._preview_thread.isRunning():
            return
        self._optimal_since = None
        self._zone_hold_since = None
        self._zone_pending = None
        self._preview_thread = CameraPreviewThread(
            camera_index=self._get_selected_camera())
        self._preview_thread.frame_ready.connect(self._on_preview_frame)
        self._preview_thread.distance_ready.connect(self._on_preview_distance)
        self._preview_thread.fingers_ready.connect(self._on_preview_fingers)
        self._preview_thread.telemetry_ready.connect(self._on_preview_telemetry)
        self._preview_thread.start()

    def _stop_preview(self):
        if self._preview_thread:
            self._preview_thread.stop()
            self._preview_thread.wait(3000)
            self._preview_thread = None

    @Slot(object)
    def _on_preview_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        if hasattr(self, "calibration_guide"):
            self.calibration_guide.set_frame(pixmap)
        if hasattr(self, "zone_guide"):
            self.zone_guide.set_frame(pixmap)

    @Slot(float, bool)
    def _on_preview_distance(self, norm_dist, has_hand):
        if hasattr(self, "calibration_guide"):
            self.calibration_guide.set_distance(norm_dist, has_hand)

        if self.home_stack.currentIndex() != 2:
            return

        _TARGET = 0.18
        _TOL    = 0.03
        optimal = has_hand and abs(norm_dist - _TARGET) <= _TOL

        if optimal:
            if self._optimal_since is None:
                self._optimal_since = time.time()
            frac = min((time.time() - self._optimal_since) / 3.0, 1.0)
            self.calibration_guide.set_progress(frac)
            if frac >= 1.0:
                self._optimal_since = None
                self.calibration_guide.set_progress(0.0)
                self._on_distance_continue()
        else:
            self._optimal_since = None
            self.calibration_guide.set_progress(0.0)

    @Slot(str, str)
    def _on_preview_telemetry(self, lighting, background):
        if hasattr(self, "calibration_guide"):
            self.calibration_guide.set_telemetry(lighting, background)

    @Slot(int, bool)
    def _on_preview_fingers(self, count, has_hand):
        if self.home_stack.currentIndex() != 3:
            self._zone_hold_since = None
            self._zone_pending = None
            return

        if not has_hand or count < 1 or count > 3:
            self._zone_hold_since = None
            self._zone_pending = None
            if hasattr(self, "zone_guide"):
                self.zone_guide.set_zone_progress(None, 0.0)
            return

        zone_map = {1: 'small', 2: 'medium', 3: 'large'}
        pending = zone_map[count]

        if pending != self._zone_pending:
            self._zone_pending = pending
            self._zone_hold_since = time.time()

        frac = min((time.time() - self._zone_hold_since) / 3.0, 1.0)
        if hasattr(self, "zone_guide"):
            self.zone_guide.set_zone_progress(pending, frac)

        if frac >= 1.0:
            self._zone_hold_since = None
            self._zone_pending = None
            if hasattr(self, "zone_guide"):
                self.zone_guide._select_zone(pending)
                self.zone_guide.set_zone_progress(None, 0.0)
            self._on_zone_continue()

    def _start_controller(self):
        zone = getattr(self.zone_guide, 'selected_zone', None) or get_saved_zone()
        self.controller = HandControllerThread(
            camera_index=self._get_selected_camera(),
            initial_zone=zone,
            skip_intro=True)
        self.controller.frame_ready.connect(self._update_frame)
        self.controller.gesture_changed.connect(self._update_gesture)
        self.controller.state_changed.connect(self._update_state)
        self.controller.error_occurred.connect(self._on_error)
        self.controller.finished.connect(self._on_finished)
        self.controller.running_data.connect(self._on_running_data)
        self.controller.stopped_data.connect(self._on_stopped_data)
        self.controller.start()

        self._is_running = True
        self._is_paused  = False
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.info_cards["STATUS"].setText("RUNNING")

    def _on_pause(self):
        if not self._is_running or not self.controller:
            return
        if self._is_paused:
            self.controller.resume()
            self._is_paused = False
            self.pause_btn.setText("Pause")
            self.start_btn.setEnabled(False)
            self.info_cards["STATUS"].setText("RUNNING")
        else:
            self.controller.pause()
            self._is_paused = True
            self.pause_btn.setText("Resume")
            self.start_btn.setEnabled(True)
            self.info_cards["STATUS"].setText("PAUSED")

    @Slot(object)
    def _on_running_data(self, data: dict):
        meta = data.get('meta', {})
        label_map = {
            'stop':     'PAUSING',
            'recal':    'RECALIBRATING',
            'guide':    'OPENING GUIDE',
            'close':    'CLOSING',
            'game_opt': 'GAME OPTION',
            'start':    'STARTING',
        }
        best_key  = max(meta, key=lambda k: meta[k], default=None)
        best_frac = meta.get(best_key, 0.0) if best_key else 0.0
        if best_frac > 0.0:
            self._show_hold_bar(label_map.get(best_key, best_key.upper()), best_frac)
        else:
            self._hide_hold_bar()

    @Slot(float, float)
    def _on_stopped_data(self, resume_frac: float, close_frac: float):
        if close_frac > 0.0:
            self._show_hold_bar("CLOSING", close_frac)
        elif resume_frac > 0.0:
            self._show_hold_bar("RESUMING", resume_frac)
        else:
            self._hide_hold_bar()

    def _show_hold_bar(self, label: str, frac: float):
        self.hold_bar_label.setText(f"● {label}")
        w = self.hold_bar_bg.width()
        if w > 0:
            self.hold_bar_fill.setGeometry(0, 0, int(frac * w), 4)

    def _hide_hold_bar(self):
        self.hold_bar_label.setText("ACTION")
        self.hold_bar_fill.setGeometry(0, 0, 0, 4)

    def _on_stop(self):
        if hasattr(self, "home_stack"):
            self.home_stack.setCurrentIndex(0)
        if self.controller and self.controller.isRunning():
            self.controller.stop()
            self.controller.wait(4000)
            self.controller = None

    @Slot()
    def _on_finished(self):
        self._hide_hold_bar()
        self._is_running = False
        self._is_paused  = False
        self.controller  = None
        self.start_btn.setEnabled(True)
        self.start_btn.setText("Start")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.stop_btn.setEnabled(False)
        self.info_cards["STATUS"].setText("Press Start")
        self._last_camera_pixmap = None
        self.camera_label.setPixmap(QPixmap())
        self.camera_label.setText("LIVE CAMERA FEED")
        if self.is_dark:
            self.camera_label.setStyleSheet("""
                background: transparent;
                color: #262626;
                font-size: 10px;
                letter-spacing: 2px;
                border: none;
            """)
            self.camera_frame.setStyleSheet("""
                background-color: #000000;
                border: 1px solid #262626;
                border-radius: 4px;
            """)
        else:
            self.camera_label.setStyleSheet("""
                background: transparent;
                color: #C9C9C9;
                font-size: 10px;
                letter-spacing: 2px;
                border: none;
            """)
            self.camera_frame.setStyleSheet("""
                background-color: #000000;
                border: 1px solid #D8D8D8;
                border-radius: 4px;
            """)

    @Slot(object)
    def _update_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        self._last_camera_pixmap = pixmap
        self._rescale_camera_frame()

    def _rescale_camera_frame(self):
        if self._last_camera_pixmap is None:
            return
        label_size = self.camera_label.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            return
        self.camera_label.setPixmap(
            self._last_camera_pixmap.scaled(
                label_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )

    def eventFilter(self, obj, event):
        if obj is getattr(self, "camera_label", None) and event.type() == QEvent.Resize:
            QTimer.singleShot(0, self._rescale_camera_frame)
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale_camera_frame()

    @Slot(str, str)
    def _update_gesture(self, gesture: str, action: str):
        self.info_cards["GESTURE"].setText(gesture.upper())
        self.info_cards["ACTION"].setText(action)

    @Slot(str)
    def _update_state(self, state: str):
        labels = {
            'intro': 'INTRO', 'zone_intro': 'ZONE',
            'zone_pick': 'PICK ZONE', 'distance_check': 'CALIBRATING',
            'running': 'RUNNING', 'stopped': 'PAUSED', 'idle': 'IDLE',
        }
        self.info_cards["STATUS"].setText(labels.get(state, state.upper()))

    @Slot(str)
    def _on_error(self, msg: str):
        self.camera_label.setText(f"⚠  {msg}")
        self._on_finished()

