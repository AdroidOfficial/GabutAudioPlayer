import os
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QIcon

app = QApplication([])

window = QWidget()
layout = QVBoxLayout()

icon_paths = [
    "icons/play.png",
    "/usr/share/icons/play.png",
    "icons/pause.png",
    "/usr/share/icons/pause.png",
    "icons/next.png",
    "/usr/share/icons/next.png",
    "icons/prev.png",
    "/usr/share/icons/prev.png"
]

for path in icon_paths:
    exists = os.path.exists(path)
    label = QLabel(f"{path} -> {'✅ Ada' if exists else '❌ Tidak ditemukan'}")
    layout.addWidget(label)

window.setLayout(layout)
window.setWindowTitle("Test Ikon")
window.show()
app.exec_()