import sys
import json
import os
import math
import psutil
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

CONFIG_FILE = "jarvis_3d_config.json"

class Jarvis3DWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(250, 250)
        
        # 3D Oktaéder csúcspontjai (X, Y, Z) koordinátarendszerben
        self.vertices = [
            (0, 1, 0),   # 0: Felső
            (0, -1, 0),  # 1: Alsó
            (1, 0, 0),   # 2: Jobb
            (-1, 0, 0),  # 3: Bal
            (0, 0, 1),   # 4: Elöl
            (0, 0, -1)   # 5: Hátul
        ]
        
        # Élek: Melyik csúcspontot melyikkel kötjük össze
        self.edges = [
            (0, 2), (0, 3), (0, 4), (0, 5), # Felsőt a középsőkkel
            (1, 2), (1, 3), (1, 4), (1, 5), # Alsót a középsőkkel
            (2, 4), (4, 3), (3, 5), (5, 2)  # Középsők egymással (Egyenlítő)
        ]
        
        # Forgási szögek
        self.angle_x = 0.0
        self.angle_y = 0.0
        self.angle_z = 0.0
        
        # Rendszer adatok
        self.cpu_usage = 0.0
        
        # Animációs időzítő (60 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(16)
        
        # Adatfrissítő időzítő (1 másodperc)
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)
        self.update_stats()
        
        self.drag_pos = None
        self.load_position()

    def update_stats(self):
        self.cpu_usage = psutil.cpu_percent()

    def update_animation(self):
        # Alap forgási sebesség + CPU terhelésből adódó extra sebesség
        speed_multiplier = 0.5 + (self.cpu_usage / 20.0)
        
        self.angle_x += 0.02 * speed_multiplier
        self.angle_y += 0.03 * speed_multiplier
        self.angle_z += 0.01 * speed_multiplier
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        #painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        center_x, center_y = w / 2, h / 2
        
        # Szín dinamikus számítása (Cián -> Vörös átmenet a CPU alapján)
        red = int(min(255, (self.cpu_usage / 100.0) * 255 * 2))
        green = int(max(0, 255 - (self.cpu_usage / 100.0) * 255))
        blue = int(max(0, 255 - (self.cpu_usage / 100.0) * 255))
        
        dynamic_color = QColor(red, green, blue, 200)
        painter.setPen(QPen(dynamic_color, 2))
        
        # 3D méretezés és megjelenítés
        scale = 60
        projected = []
        
        # Csúcspontok 3D forgatása és 2D vetítése
        for v in self.vertices:
            x, y, z = v
            
            # X tengely körüli forgatás
            y1 = y * math.cos(self.angle_x) - z * math.sin(self.angle_x)
            z1 = y * math.sin(self.angle_x) + z * math.cos(self.angle_x)
            
            # Y tengely körüli forgatás
            x2 = x * math.cos(self.angle_y) + z1 * math.sin(self.angle_y)
            z2 = -x * math.sin(self.angle_y) + z1 * math.cos(self.angle_y)
            
            # Z tengely körüli forgatás
            x3 = x2 * math.cos(self.angle_z) - y1 * math.sin(self.angle_z)
            y3 = x2 * math.sin(self.angle_z) + y1 * math.cos(self.angle_z)
            
            # Orto-grafikus vetítés (2D képernyőre)
            x_proj = x3 * scale + center_x
            y_proj = y3 * scale + center_y
            projected.append((x_proj, y_proj))
            
            # Csomópontok rajzolása (kis körök a sarkokon)
            painter.setBrush(dynamic_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(x_proj - 3), int(y_proj - 3), 6, 6)
            
        # Élek megrajzolása
        painter.setPen(QPen(dynamic_color, 1.5))
        for edge in self.edges:
            start_p = projected[edge[0]]
            end_p = projected[edge[1]]
            painter.drawLine(int(start_p[0]), int(start_p[1]), int(end_p[0]), int(end_p[1]))

        # Adatkijelzés a sarokban
        font = QFont("Consolas", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(220, 255, 255, 180))
        painter.drawText(10, h - 10, f"STRUCTURAL LOAD: {self.cpu_usage}%")

    # --- Ablak mozgatása, bezárása, pozíció mentése ---
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
            except Exception:
                pass

    def save_position(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'x': self.pos().x(), 'y': self.pos().y()}, f)
        except Exception:
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = Jarvis3DWidget()
    widget.show()
    sys.exit(app.exec())