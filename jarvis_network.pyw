import sys
import psutil
import json
import os
from collections import deque
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

CONFIG_FILE = "jarvis_net_config.json"

class JarvisNetworkWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Háttérben futó, keret nélküli ablak
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(300, 150)
        
        # Hálózati adatok tárolása (utolsó 40 másodperc)
        self.history_len = 40
        self.dl_history = deque([0] * self.history_len, maxlen=self.history_len)
        self.ul_history = deque([0] * self.history_len, maxlen=self.history_len)
        
        # Kezdeti hálózati állapot
        self.last_net = psutil.net_io_counters()
        
        # Időzítő a frissítéshez (1 másodpercenként)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_network_stats)
        self.timer.start(1000)
        
        self.drag_pos = None
        self.load_position()

    def update_network_stats(self):
        current_net = psutil.net_io_counters()
        
        # Sebesség kiszámítása (Megabyte / sec)
        dl_speed = (current_net.bytes_recv - self.last_net.bytes_recv) / 1024 / 1024
        ul_speed = (current_net.bytes_sent - self.last_net.bytes_sent) / 1024 / 1024
        self.last_net = current_net
        
        self.dl_history.append(dl_speed)
        self.ul_history.append(ul_speed)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        #painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # --- Futurisztikus Keret Rajzolása ---
        pen_frame = QPen(QColor(0, 255, 255, 120), 2)
        painter.setPen(pen_frame)
        
        # Szögletes sarokelemek (HUD stílus)
        w, h = self.width(), self.height()
        painter.drawLine(10, 30, 10, 10) # Bal felső
        painter.drawLine(10, 10, 30, 10)
        painter.drawLine(w-30, 10, w-10, 10) # Jobb felső
        painter.drawLine(w-10, 10, w-10, 30)
        painter.drawLine(10, h-30, 10, h-10) # Bal alsó
        painter.drawLine(10, h-10, 30, h-10)
        painter.drawLine(w-30, h-10, w-10, h-10) # Jobb alsó
        painter.drawLine(w-10, h-10, w-10, h-30)

        # --- Szövegek ---
        painter.setPen(QColor(220, 255, 255, 200))
        font = QFont("Consolas", 9, QFont.Weight.Bold)
        painter.setFont(font)
        
        dl_current = self.dl_history[-1]
        ul_current = self.ul_history[-1]
        
        painter.drawText(20, 25, "J.A.R.V.I.S. UPLINK")
        painter.drawText(20, h - 20, f"DL: {dl_current:.2f} MB/s")
        painter.drawText(w - 120, h - 20, f"UL: {ul_current:.2f} MB/s")

        # --- Diagram Rajzolása ---
        bar_width = (w - 40) / self.history_len
        
        # Dinamikus skálázás (hogy mindig kitöltse a keretet)
        max_dl = max(self.dl_history) if max(self.dl_history) > 0.1 else 0.1
        
        painter.setPen(Qt.PenStyle.NoPen)
        for i, val in enumerate(self.dl_history):
            # Oszlopmagasság számítása
            bar_h = (val / max_dl) * (h - 60)
            
            # Halványuló hatás a régebbi adatoknál
            alpha = int(50 + (205 * (i / self.history_len)))
            painter.setBrush(QColor(0, 255, 255, alpha)) # Ciánkék
            
            # Oszlop rajzolása lentről felfelé
            x = int(20 + i * bar_width)
            y = int(h - 40 - bar_h)
            painter.drawRect(x, y, int(bar_width - 1), int(bar_h))

    # --- Pozíció kezelése és Egér események ---
    def load_position(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    pos = json.load(f)
                    self.move(pos['x'], pos['y'])
            except Exception:
                pass

    def save_position(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'x': self.pos().x(), 'y': self.pos().y()}, f)
        except Exception:
            pass

    def closeEvent(self, event):
        self.save_position()
        event.accept()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()
        elif event.button() == Qt.MouseButton.RightButton:
            self.close()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        self.save_position()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = JarvisNetworkWidget()
    widget.show()
    sys.exit(app.exec())