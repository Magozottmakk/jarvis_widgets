import sys
import psutil
import json
import os
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

CONFIG_FILE = "jarvis_config.json"

class JarvisSystemWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Ablak beállítások: keret nélkül, háttérben futó tool ablak (nem takarja el a többi ablakot)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(320, 320)
        
        # Forgási szögek alaphelyzete
        self.angle_outer = 0
        self.angle_middle = 0
        self.angle_inner = 0
        
        # Rendszeradatok változói
        self.cpu_usage = 0.0
        self.ram_usage = 0.0
        
        # Időzítők
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(16)
        
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_system_stats)
        self.stats_timer.start(1000)
        
        self.update_system_stats()
        self.drag_pos = None
        
        # Előző pozíció betöltése, ha létezik
        self.load_position()

    def update_animation(self):
        self.angle_outer = (self.angle_outer + 1.0) % 360
        self.angle_middle = (self.angle_middle - 1.5) % 360
        self.angle_inner = (self.angle_inner + 3.0) % 360
        self.update()

    def update_system_stats(self):
        self.cpu_usage = psutil.cpu_percent()
        self.ram_usage = psutil.virtual_memory().percent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        
        def draw_ring(radius, span_angle, start_angle, rotation, color, thickness):
            painter.save()
            painter.translate(center)
            painter.rotate(rotation)
            
            pen = QPen(color, thickness)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
            painter.drawArc(-radius, -radius, radius * 2, radius * 2, int(start_angle * 16), int(span_angle * 16))
            painter.restore()

        cyan_glow = QColor(0, 255, 255, 180)
        blue_glow = QColor(0, 130, 255, 140)
        orange_alert = QColor(255, 100, 0, 160)
        white_core = QColor(220, 255, 255, 200)

        cpu_span = max(5, (self.cpu_usage / 100.0) * 80)
        for i in range(4):
            draw_ring(130, cpu_span, i * 90, self.angle_outer, orange_alert, 4)

        ram_span = max(5, (self.ram_usage / 100.0) * 110)
        for i in range(3):
            draw_ring(100, ram_span, i * 120, self.angle_middle, blue_glow, 7)

        for i in range(2):
            draw_ring(70, 90, i * 180, self.angle_inner, cyan_glow, 2)
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 255, 255, 25))
        painter.drawEllipse(center, 48, 48)

        painter.setPen(white_core)
        font = QFont("Consolas", 10, QFont.Weight.Bold)
        painter.setFont(font)
        
        cpu_text = f"CPU: {int(self.cpu_usage)}%"
        ram_text = f"RAM: {int(self.ram_usage)}%"
        
        painter.drawText(center.x() - 32, center.y() - 4, cpu_text)
        painter.drawText(center.x() - 32, center.y() + 16, ram_text)

    # --- Pozíció mentése és betöltése ---

    def load_position(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    pos = json.load(f)
                    self.move(pos['x'], pos['y'])
            except Exception as e:
                print(f"Hiba a pozíció betöltésekor: {e}")

    def save_position(self):
        pos = {
            'x': self.pos().x(),
            'y': self.pos().y()
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(pos, f)
        except Exception as e:
            print(f"Hiba a pozíció mentésekor: {e}")

    # Esemény, ami akkor fut le, amikor az ablak bezáródik
    def closeEvent(self, event):
        self.save_position()
        event.accept()

    # --- Egérvezérlés ---
    
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
        # Opcionális: Akár minden elengedéskor is menthetjük az új pozíciót
        self.save_position()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = JarvisSystemWidget()
    widget.show()
    sys.exit(app.exec())