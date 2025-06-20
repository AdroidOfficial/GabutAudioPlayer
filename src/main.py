#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSlider, QLabel,
                             QFileDialog, QListWidget, QStatusBar, QAction,
                             QMessageBox, QMenu, QDialog, QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtGui import QIcon, QFont, QColor 
from PyQt5.QtCore import Qt, QTimer, QUrl ,QSize
import vlc
from urllib.parse import unquote
import pickle


class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_style = ""
        self.hover_style = ""

    def set_button_styles(self, base_style, hover_style):
        self.base_style = base_style
        self.hover_style = hover_style
        self.setStyleSheet(base_style)

    def enterEvent(self, event):
        if self.hover_style:
            self.setStyleSheet(self.hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.base_style:
            self.setStyleSheet(self.base_style)
        super().leaveEvent(event)


class GabutAudioPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G.A.P")
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Base path
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        icon_app = self.get_icon_path("GAP.png")
        self.setWindowIcon(QIcon(icon_app))

        # Direktori konfigurasi
        self.config_dir = os.path.expanduser("~/.config/gabutaudioplayer")
        os.makedirs(self.config_dir, exist_ok=True)
        self.playlist_file = os.path.join(self.config_dir, "playlist.pkl")
        self.theme_file = os.path.join(self.config_dir, "theme.pkl")
        self.opacity_file = os.path.join(self.config_dir, "opacity.pkl")
        self.playlist_count = 0
        self.playlist_paths = []
        self.current_theme = "grey"
        self.opacity = 0.9  # Default opacity
        self.drag_position = None

        # Inisialisasi VLC
        self.vlc_instance = vlc.Instance("--no-video-title-show")
        self.media_player = self.vlc_instance.media_player_new()
        self.media_list = self.vlc_instance.media_list_new([])
        self.media_list_player = self.vlc_instance.media_list_player_new()
        self.media_list_player.set_media_player(self.media_player)
        self.media_list_player.set_media_list(self.media_list)

        # Setup UI
        self.setup_ui()

        # Load settings
        self.load_theme()
        self.load_opacity()

        # Load playlist
        self.load_playlist()

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.update_status_bar()

        # Timer update progress
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(1000)

        # Volume awal
        self.media_player.audio_set_volume(70)

        # Apply initial theme
        self.apply_current_theme()

    def get_icon_path(self, icon_name):
        system_path = f"/usr/share/gabutaudioplayer/icons/{icon_name}"
        if os.path.exists(system_path):
            return system_path
        return os.path.join(self.base_path, "icons", icon_name)

    def update_status_bar(self):
        self.statusBar.showMessage(f"♪ {self.playlist_count} tracks loaded")

    def setup_ui(self):
        main_widget = QWidget()
        main_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(20)

        # Header Navigation + Tombol Close
        header_container = QFrame()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(50)
        self.add_shadow_effect(self.header_frame)
        header_inner = QHBoxLayout(self.header_frame)
        header_inner.setContentsMargins(15, 8, 15, 8)
        header_inner.setSpacing(10)

        self.title_label = QLabel("G.A.P")
        self.title_label.setFont(QFont("Poppins", 16, QFont.Bold))
        header_inner.addWidget(self.title_label)
        header_inner.addStretch()

        self.files_button = AnimatedButton("📁")
        self.tentang_button = AnimatedButton("👪")
        self.close_button = AnimatedButton("✕")

        for btn in [self.files_button, self.tentang_button, self.close_button]:
            btn.setFixedSize(35, 35)

        header_inner.addWidget(self.files_button)
        header_inner.addWidget(self.tentang_button)
        header_inner.addWidget(self.close_button)

        header_layout.addWidget(self.header_frame)
        layout.addWidget(header_container)

        # Track Info + Progress Bar
        self.track_info_frame = QFrame()
        self.track_info_frame.setFixedHeight(180)
        self.add_shadow_effect(self.track_info_frame)
        track_info_layout = QVBoxLayout(self.track_info_frame)
        track_info_layout.setContentsMargins(10, 5, 10, 5)
        track_info_layout.setSpacing(5)

        self.track_info = QLabel("Ready to play...")
        self.track_info.setAlignment(Qt.AlignCenter)
        self.track_info.setFont(QFont("Poppins", 12, QFont.Medium))
        self.track_info.setWordWrap(True)
        track_info_layout.addWidget(self.track_info)

        time_layout = QHBoxLayout()
        self.current_time = QLabel("0:00")
        self.total_time = QLabel("0:00")
        for label in [self.current_time, self.total_time]:
            label.setFont(QFont("Poppins", 9))
        time_layout.addWidget(self.current_time)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time)
        track_info_layout.addLayout(time_layout)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setFixedHeight(25)
        self.progress_slider.sliderMoved.connect(self.seek_position)
        track_info_layout.addWidget(self.progress_slider)

        layout.addWidget(self.track_info_frame)

        # Tombol Kontrol
        self.control_frame = QFrame()
        self.control_frame.setFixedHeight(80)
        self.add_shadow_effect(self.control_frame)
        control_layout = QHBoxLayout(self.control_frame)
        control_layout.setContentsMargins(20, 15, 20, 15)

        self.prev_button = AnimatedButton()
        self.next_button = AnimatedButton()
        self.play_button = AnimatedButton()

        icon_play = self.get_icon_path("play.png")
        icon_pause = self.get_icon_path("pause.png")
        icon_prev = self.get_icon_path("prev.png")
        icon_next = self.get_icon_path("next.png")

        self.prev_button.setIcon(QIcon(icon_prev))
        self.next_button.setIcon(QIcon(icon_next))
        self.play_button.setIcon(QIcon(icon_play))

        self.prev_button.setIconSize(QSize(32, 32))
        self.next_button.setIconSize(QSize(32, 32))
        self.play_button.setIconSize(QSize(32, 32))

        self.prev_button.setFixedSize(45, 45)
        self.next_button.setFixedSize(45, 45)
        self.play_button.setFixedSize(55, 55)

        control_layout.addStretch()
        control_layout.addWidget(self.prev_button)
        control_layout.addSpacing(20)
        control_layout.addWidget(self.play_button)
        control_layout.addSpacing(20)
        control_layout.addWidget(self.next_button)
        control_layout.addStretch()

        layout.addWidget(self.control_frame)

        # Volume Control
        self.volume_frame = QFrame()
        volume_layout = QHBoxLayout(self.volume_frame)
        volume_layout.setContentsMargins(15, 8, 15, 8)

        self.volume_icon = QLabel("🔊")
        self.volume_icon.setStyleSheet("font-size: 16px; background: transparent;")

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedHeight(18)

        self.volume_label = QLabel("70%")
        self.volume_label.setFixedWidth(35)
        self.volume_label.setFont(QFont("Poppins", 9))

        volume_layout.addWidget(self.volume_icon)
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.volume_label)

        layout.addWidget(self.volume_frame)
        layout.addStretch()

        self.setCentralWidget(main_widget)

        # Connect signals
        self.files_button.clicked.connect(self.show_files_menu)
        self.tentang_button.clicked.connect(self.show_about_dialog)
        self.play_button.clicked.connect(self.toggle_playback)
        self.next_button.clicked.connect(self.next_track)
        self.prev_button.clicked.connect(self.previous_track)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.close_button.clicked.connect(self.close)

        # Mouse drag support
        self.mousePressEvent = self.mouse_press_event
        self.mouseMoveEvent = self.mouse_move_event

        # Update ikon play/pause
        self.icon_play = QIcon(icon_play)
        self.icon_pause = QIcon(icon_pause)

    def mouse_press_event(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouse_move_event(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def add_shadow_effect(self, widget):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 80))
        widget.setGraphicsEffect(shadow)

    def toggle_playback(self):
        if self.playlist_count == 0:
            QMessageBox.warning(self, "Musik Kosong Gan, Tambah Lagu Dulu!", "Playlist not found!")
            return
        if self.media_player.is_playing():
            self.media_player.pause()
            self.play_button.setIcon(self.icon_play)
        else:
            self.media_list_player.play()
            self.play_button.setIcon(self.icon_pause)

    def next_track(self):
        self.media_list_player.next()

    def previous_track(self):
        self.media_list_player.previous()

    def seek_position(self, position):
        duration = self.media_player.get_length()
        if duration > 0:
            new_time = int(duration * (position / 100))
            self.media_player.set_time(new_time)

    def set_volume(self, value):
        self.media_player.audio_set_volume(value)
        self.volume_label.setText(f"{value}%")

    def update_progress(self):
        if self.media_player.is_playing():
            duration = self.media_player.get_length()
            current = self.media_player.get_time()
            if duration > 0:
                percentage = int((current / duration) * 100)
                self.progress_slider.blockSignals(True)
                self.progress_slider.setValue(percentage)
                self.progress_slider.blockSignals(False)
                self.current_time.setText(self.format_time(current))
                self.total_time.setText(self.format_time(duration))
                self.update_track_info()

    def update_track_info(self):
        index = self.media_list_player.get_media_player().get_media()
        if index:
            try:
                mrl = index.get_mrl()
                path = unquote(QUrl(mrl).toLocalFile())
                self.track_info.setText(os.path.basename(path))
            except:
                self.track_info.setText("Playing...")

    def format_time(self, ms):
        seconds = ms // 1000
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes}:{seconds:02d}"

    def load_theme(self):
        if os.path.exists(self.theme_file):
            try:
                with open(self.theme_file, "rb") as f:
                    theme = pickle.load(f)
                    if theme in ["grey", "transparent"]:
                        self.current_theme = theme
            except Exception as e:
                print("Error loading theme:", e)
        else:
            self.current_theme = "grey"

    def load_opacity(self):
        if os.path.exists(self.opacity_file):
            try:
                with open(self.opacity_file, "rb") as f:
                    self.opacity = pickle.load(f)
            except Exception as e:
                print("Error loading opacity:", e)
        else:
            self.opacity = 0.9

    def save_theme(self):
        try:
            with open(self.theme_file, "wb") as f:
                pickle.dump(self.current_theme, f)
        except Exception as e:
            print("Error saving theme:", e)

    def save_opacity(self):
        try:
            with open(self.opacity_file, "wb") as f:
                pickle.dump(self.opacity, f)
        except Exception as e:
            print("Error saving opacity:", e)

    def apply_current_theme(self):
        if self.current_theme == "transparent":
            self.set_transparent_mode_styles()
        else:
            self.set_grey_mode_styles()

    def show_about_dialog(self):
        about_text = """
        <h2>Gabut Audio Player</h2>
        <p><b>Versi:</b> 2.0</p>
        <p><b>Pembuat:</b> Andro Atarodang</p>
        <p>Aplikasi pemutar audio sederhana.</p>
        <p><b>Lisensi:</b> MIT License</p>
        """
        QMessageBox.about(self, "Tentang Aplikasi", about_text)

    def show_files_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #00d4aa;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item:selected {
                background-color: #00d4aa;
                color: #1a1a1a;
            }
        """)
        open_folder_action = menu.addAction("📁 Buka Folder")
        view_playlist_action = menu.addAction("📝 List Lagu")
        grey_mode_action = menu.addAction("🌑 Soft Dark")
        transparent_mode_action = menu.addAction("🌫️ Transparent Mode")
        open_folder_action.triggered.connect(self.open_folder)
        view_playlist_action.triggered.connect(self.view_playlist)
        grey_mode_action.triggered.connect(lambda: self.set_theme("grey"))
        transparent_mode_action.triggered.connect(lambda: self.show_opacity_dialog())
        menu.exec_(self.files_button.mapToGlobal(self.files_button.rect().bottomLeft()))

    def load_playlist(self):
        if os.path.exists(self.playlist_file):
            try:
                with open(self.playlist_file, "rb") as f:
                    self.playlist_paths = pickle.load(f)
                    for path in self.playlist_paths:
                        if os.path.exists(path):
                            media = self.vlc_instance.media_new(path)
                            self.media_list.add_media(media)
                            self.playlist_count += 1
                    self.update_status_bar()
            except Exception as e:
                print("Failed to load playlist:", e)

    def closeEvent(self, event):
        try:
            with open(self.playlist_file, "wb") as f:
                pickle.dump(self.playlist_paths, f)
        except Exception as e:
            print("Failed to save playlist:", e)
        event.accept()

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Lagu")
        if folder:
            valid_ext = ('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac')
            for root, _, filenames in os.walk(folder):
                for f in filenames:
                    if f.lower().endswith(valid_ext):
                        self.add_to_playlist(os.path.join(root, f))

    def add_to_playlist(self, file):
        media = self.vlc_instance.media_new(file)
        self.media_list.add_media(media)
        self.playlist_paths.append(file)
        self.playlist_count += 1
        self.update_status_bar()

    def view_playlist(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Daftar Lagu")
        dialog.setFixedSize(500, 500)
        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        for path in self.playlist_paths:
            list_widget.addItem(os.path.basename(path))

        def on_double_click(item):
            index = list_widget.row(item)
            if index >= 0:
                self.media_list_player.play_item_at_index(index)
                self.media_player.play()
                self.play_button.setIcon(self.icon_pause)

        list_widget.itemDoubleClicked.connect(on_double_click)
        layout.addWidget(list_widget)
        dialog.exec_()

    def show_opacity_dialog(self):
        from PyQt5.QtWidgets import QSlider, QLabel, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Opacity")
        dialog.setFixedSize(300, 120)
        layout = QVBoxLayout(dialog)
        label = QLabel(f"Opacity: {int(self.opacity * 100)}%")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(40, 100)
        slider.setValue(int(self.opacity * 100))
        slider.valueChanged.connect(lambda val: label.setText(f"Opacity: {val}%"))
        slider.sliderReleased.connect(lambda: self.set_custom_opacity(slider.value()))
        layout.addWidget(label)
        layout.addWidget(slider)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec_()

    def set_custom_opacity(self, val):
        self.opacity = val / 100
        self.set_theme("transparent")
        self.save_opacity()

    def set_theme(self, theme):
        self.current_theme = theme
        self.apply_current_theme()
        self.save_theme()

    def apply_current_theme(self):
        if self.current_theme == "transparent":
            self.set_transparent_mode_styles()
        else:
            self.set_grey_mode_styles()

    def get_slider_style(self, theme="grey"):
        if theme == "transparent":
            return """
                QSlider::groove:horizontal {
                    background: rgba(255, 255, 255, 0.2);
                    height: 4px;
                    border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #00d4aa;
                    width: 14px;
                    height: 14px;
                    margin: -5px 0;
                    border-radius: 7px;
                    border: 1px solid #ffffff;
                }
                QSlider::handle:horizontal:hover {
                    background: #00f4cc;
                }
                QSlider::sub-page:horizontal {
                    background: #00d4aa;
                }
            """
        else:
            return """
                QSlider::groove:horizontal {
                    background: rgba(0, 0, 0, 0.5);
                    height: 4px;
                    border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #007acc;
                    width: 14px;
                    height: 14px;
                    margin: -5px 0;
                    border-radius: 7px;
                    border: 1px solid #000000;
                }
                QSlider::handle:horizontal:hover {
                    background: #0099ff;
                }
                QSlider::sub-page:horizontal {
                    background: #007acc;
                }
            """

    def set_grey_mode_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background: rgba(30, 30, 30, 1.0);
                border-radius: 15px;
            }
        """)
        self.header_frame.setStyleSheet("""
            QFrame {
                background: rgba(45, 45, 45, 1.0);
                border-radius: 15px;
                border: 1px solid rgba(60, 60, 60, 1.0);
            }
        """)
        self.title_label.setStyleSheet("color: #cccccc; background: transparent;")
        header_button_base = """
            QPushButton {
                background-color: #3d3d3d;
                color: #aaaaaa;
                border-radius: 17px;
                font-size: 16px;
                border: 1px solid rgba(60, 60, 60, 0.5);
            }
        """
        header_button_hover = """
            QPushButton {
                background-color: #555555;
                color: #ffffff;
                border-radius: 17px;
                font-size: 16px;
                border: 1px solid #888888;
            }
        """
        close_button_base = """
            QPushButton {
                background-color: #3d3d3d;
                color: #cc6666;
                border-radius: 17px;
                font-size: 16px;
                border: 1px solid rgba(120, 50, 50, 0.3);
            }
        """
        close_button_hover = """
            QPushButton {
                background-color: #555555;
                color: #ff6666;
                border-radius: 17px;
                font-size: 16px;
                border: 1px solid #ff6666;
            }
        """
        self.files_button.set_button_styles(header_button_base, header_button_hover)
        self.tentang_button.set_button_styles(header_button_base, header_button_hover)
        self.close_button.set_button_styles(close_button_base, close_button_hover)

        self.track_info_frame.setStyleSheet("""
            QFrame {
                background: rgba(40, 40, 40, 1.0);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        self.track_info.setStyleSheet("color: #dddddd; background: transparent;")
        self.current_time.setStyleSheet("color: rgba(220, 220, 220, 0.7); background: transparent;")
        self.total_time.setStyleSheet("color: rgba(220, 220, 220, 0.7); background: transparent;")
        self.control_frame.setStyleSheet("""
            QFrame {
                background: rgba(45, 45, 45, 1.0);
                border-radius: 15px;
                border: 1px solid rgba(60, 60, 60, 1.0);
            }
        """)
        control_button_base = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #3d3d3d, stop: 1 #2e2e2e);
                color: #bbbbbb;
                border-radius: 22px;
                font-size: 16px;
                border: 1px solid rgba(60, 60, 60, 0.3);
            }
        """
        control_button_hover = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #555555, stop: 1 #444444);
                color: #ffffff;
                border-radius: 22px;
                font-size: 16px;
                border: 1px solid #888888;
            }
        """
        play_button_base = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #444444, stop: 1 #333333);
                color: #ffffff;
                border-radius: 27px;
                font-size: 20px;
                font-weight: bold;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
        """
        play_button_hover = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #555555, stop: 1 #444444);
                color: #ffffff;
                border-radius: 27px;
                font-size: 20px;
                font-weight: bold;
                border: 2px solid rgba(255, 255, 255, 0.4);
            }
        """
        self.prev_button.set_button_styles(control_button_base, control_button_hover)
        self.next_button.set_button_styles(control_button_base, control_button_hover)
        self.play_button.set_button_styles(play_button_base, play_button_hover)
        self.volume_frame.setStyleSheet("""
            QFrame {
                background: rgba(40, 40, 40, 1.0);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        self.volume_icon.setStyleSheet("color: #aaaaaa; font-size: 16px; background: transparent;")
        self.volume_label.setStyleSheet("color: rgba(220, 220, 220, 0.8); background: transparent;")
        self.statusBar.setStyleSheet("""
            QStatusBar {
                background: transparent;
                color: #999;
                border: none;
                font-size: 11px;
                padding: 2px 10px;
            }
        """)
        self.progress_slider.setStyleSheet(self.get_slider_style("grey"))
        self.volume_slider.setStyleSheet(self.get_slider_style("grey"))

    def set_transparent_mode_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: rgba(26, 26, 26, {self.opacity});
                border-radius: 15px;
            }}
        """)
        self.header_frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, {0.05 + (1-self.opacity)*0.1});
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, {0.1 + (1-self.opacity)*0.2});
            }}
        """)
        self.title_label.setStyleSheet("color: #00d4aa; background: transparent;")
        header_button_base = f"""
            QPushButton {{
                background-color: rgba(26, 26, 26, {self.opacity});
                color: #00d4aa;
                border-radius: 17px;
                font-size: 16px;
                border: 1px solid rgba(0, 212, 170, {0.3 + (1-self.opacity)*0.2});
            }}
        """
        header_button_hover = f"""
            QPushButton {{
                background-color: rgba(45, 45, 45, {min(1.0, self.opacity + 0.2)});
                color: #00d4aa;
                border-radius: 17px;
                font-size: 16px;
                border: 1px solid #00d4aa;
            }}
        """
        close_button_base = f"""
            QPushButton {{
                background-color: rgba(26, 26, 26, {self.opacity});
                color: #ff4b5c;
                border-radius: 17px;
                font-size: 16px;
                border: 1px solid rgba(255, 75, 92, {0.3 + (1-self.opacity)*0.2});
            }}
        """
        close_button_hover = f"""
            QPushButton {{
                background-color: rgba(45, 45, 45, {min(1.0, self.opacity + 0.2)});
                color: #ff4b5c;
                border-radius: 17px;
                font-size: 16px;
                border: 1px solid #ff6666;
            }}
        """
        self.files_button.set_button_styles(header_button_base, header_button_hover)
        self.tentang_button.set_button_styles(header_button_base, header_button_hover)
        self.close_button.set_button_styles(close_button_base, close_button_hover)
        self.track_info_frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, {0.03 + (1-self.opacity)*0.05});
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        self.track_info.setStyleSheet("color: white; background: transparent;")
        self.current_time.setStyleSheet("color: rgba(255, 255, 255, 0.7); background: transparent;")
        self.total_time.setStyleSheet("color: rgba(255, 255, 255, 0.7); background: transparent;")
        self.control_frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, {0.05 + (1-self.opacity)*0.1});
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, {0.1 + (1-self.opacity)*0.2});
            }}
        """)
        control_alpha = min(1.0, self.opacity + 0.3)
        control_button_base = f"""
            QPushButton {{
                background: rgba(42, 42, 42, {control_alpha});
                color: #ffffff;
                border-radius: 22px;
                font-size: 16px;
                border: 1px solid rgba(255, 255, 255, {0.1 + (1-self.opacity)*0.2});
            }}
        """
        control_button_hover = f"""
            QPushButton {{
                background: rgba(58, 58, 58, {min(1.0, control_alpha + 0.2)});
                color: #ffffff;
                border-radius: 22px;
                font-size: 16px;
                border: 1px solid rgba(0, 212, 170, 0.5);
            }}
        """
        self.prev_button.set_button_styles(control_button_base, control_button_hover)
        self.next_button.set_button_styles(control_button_base, control_button_hover)
        play_button_base = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #00d4aa, stop: 1 #00a688);
                color: #ffffff;
                border-radius: 27px;
                font-size: 20px;
                font-weight: bold;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
        """
        play_button_hover = """
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                              stop: 0 #00f4cc, stop: 1 #00d4aa);
                color: #ffffff;
                border-radius: 27px;
                font-size: 20px;
                font-weight: bold;
                border: 2px solid rgba(255, 255, 255, 0.4);
            }
        """
        self.play_button.set_button_styles(play_button_base, play_button_hover)
        self.volume_frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(255, 255, 255, {0.03 + (1-self.opacity)*0.05});
                border-radius: 10px;
                padding: 5px;
            }}
        """)
        self.volume_icon.setStyleSheet("color: #00d4aa; font-size: 16px; background: transparent;")
        self.volume_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); background: transparent;")
        self.statusBar.setStyleSheet("""
            QStatusBar {
                background: transparent;
                color: #888;
                border: none;
                font-size: 11px;
                padding: 2px 10px;
            }
        """)
        self.progress_slider.setStyleSheet(self.get_slider_style("transparent"))
        self.volume_slider.setStyleSheet(self.get_slider_style("transparent"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GabutAudioPlayer()
    window.show()
    sys.exit(app.exec_())
