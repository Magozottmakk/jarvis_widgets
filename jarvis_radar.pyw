import sys
import json
import os
import urllib.request
from PyQt6.QtWidgets import QApplication, QWidget, QSizeGrip
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QConicalGradient

CONFIG_FILE = "jarvis_radar_config.json"

class JarvisRadarWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Alapértelmezett méret (később a config felülírja, ha már elmentetted)
        self.resize(400, 200)
        
        # --- Méretező Fogantyú (Size Grip) ---
        self.grip = QSizeGrip(self)
        # Átlátszóvá tesszük a Windows-os szürke pöttyöket, mert sajátot rajzolunk
        self.grip.setStyleSheet("background: transparent;")
        
        # Radar animációs változók
        self.radar_angle = 0.0
        self.blink_alpha = 255
        self.blink_fade = True
        
        self.iss_lat = 0.0
        self.iss_lon = 0.0
        self.has_data = False
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(16)
        
        self.api_timer = QTimer(self)
        self.api_timer.timeout.connect(self.fetch_iss_data)
        self.api_timer.start(5000)
        
        self.fetch_iss_data()
        
        self.drag_pos = None
        self.load_position()

    # Esemény, ami akkor fut le, ha átméretezik az ablakot
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # A fogantyút mindig a jobb alsó sarokba mozgatjuk
        self.grip.resize(20, 20)
        self.grip.move(self.width() - 20, self.height() - 20)

    def update_animation(self):
        self.radar_angle = (self.radar_angle - 2.0) % 360
        
        if self.blink_fade:
            self.blink_alpha -= 5
            if self.blink_alpha <= 50:
                self.blink_fade = False
        else:
            self.blink_alpha += 5
            if self.blink_alpha >= 255:
                self.blink_fade = True
                
        self.update()

    def fetch_iss_data(self):
        try:
            req = urllib.request.Request(
                "http://api.open-notify.org/iss-now.json", 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=2.0) as response:
                data = json.loads(response.read().decode())
                self.iss_lat = float(data['iss_position']['latitude'])
                self.iss_lon = float(data['iss_position']['longitude'])
                self.has_data = True
        except Exception:
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        #painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        center = QPointF(w / 2, h / 2)
        
        cyan_dim = QColor(0, 255, 255, 40)
        cyan_bright = QColor(0, 255, 255, 180)
        
        # --- 1. Háttér Rácsozat ---
        painter.setPen(QPen(cyan_dim, 1))
        for i in range(1, 5):
            painter.drawLine(0, int(i * (h/5)), w, int(i * (h/5)))
        for i in range(1, 10):
            painter.drawLine(int(i * (w/10)), 0, int(i * (w/10)), h)
            
        painter.setPen(QPen(cyan_bright, 1))
        painter.drawLine(0, int(h/2), w, int(h/2))
        painter.drawLine(int(w/2), 0, int(w/2), h)

        # --- 2. Forgó Radarszkenner ---
        gradient = QConicalGradient(center, self.radar_angle)
        gradient.setColorAt(0.0, QColor(0, 255, 255, 100))
        gradient.setColorAt(0.1, QColor(0, 255, 255, 0))
        gradient.setColorAt(1.0, QColor(0, 255, 255, 0))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        radius = max(w, h)
        painter.drawEllipse(center, radius, radius)

        # --- 3. Átméretező sarok rajzolása (Jobb alsó) ---
        painter.setPen(QPen(cyan_bright, 2))
        # Két rövid vonal, ami egy sarkot mutat, jelezve, hogy ott húzható
        painter.drawLine(w - 15, h - 5, w - 5, h - 5)
        painter.drawLine(w - 5, h - 15, w - 5, h - 5)
        # Plusz egy apró átlós vonal textúrának
        painter.drawLine(w - 10, h - 5, w - 5, h - 10)

        # --- 4. ISS Pozíció ---
        if self.has_data:
            x = (self.iss_lon + 180.0) * (w / 360.0)
            y = (90.0 - self.iss_lat) * (h / 180.0)
            
            iss_pos = QPointF(x, y)
            
            alert_color = QColor(255, 50, 50, self.blink_alpha)
            painter.setPen(QPen(alert_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            painter.drawEllipse(iss_pos, 6, 6)
            painter.drawLine(int(x - 12), int(y), int(x - 4), int(y))
            painter.drawLine(int(x + 4), int(y), int(x + 12), int(y))
            painter.drawLine(int(x), int(y - 12), int(x), int(y - 4))
            painter.drawLine(int(x), int(y + 4), int(x), int(y + 12))
            
            font = QFont("Consolas", max(7, int(w/50)), QFont.Weight.Bold) # Szöveg mérete is skálázódik minimálisan
            painter.setFont(font)
            painter.setPen(QColor(220, 220, 220, 255))
            painter.drawText(int(x + 10), int(y - 10), "ISS [UPLINK]")
            
            painter.setPen(cyan_bright)
            coord_text = f"TRACKING ISS - LAT: {self.iss_lat:.2f} LON: {self.iss_lon:.2f}"
            painter.drawText(5, h - 5, coord_text)

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

    def load_position(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    pos = json.load(f)
                    self.move(pos['x'], pos['y'])
                    # Ha már van mentett méret (W, H), azt is betöltjük
                    if 'w' in pos and 'h' in pos:
                        self.resize(pos['w'], pos['h'])
            except Exception:
                pass

    def save_position(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                # Elmentjük az X, Y pozíciót, ÉS a szélességet (W), magasságot (H)
                json.dump({
                    'x': self.pos().x(), 
                    'y': self.pos().y(),
                    'w': self.width(),
                    'h': self.height()
                }, f)
        except Exception:
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = JarvisRadarWidget()
    widget.show()
    sys.exit(app.exec())