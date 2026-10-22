import sys
import json
import os
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QTime, QDate
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

CONFIG_FILE = "jarvis_clock_config.json"

class JarvisClockWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Ablak beállítások: keret nélkül, háttérben futó tool ablak
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(260, 260)
        
        # Forgási szög a radarhoz/célkereszthez
        self.angle_radar = 0.0
        self.angle_inner = 0.0
        
        # Animációs időzítő (folyamatos, sima forgás)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(20) # 50 FPS
        
        self.drag_pos = None
        self.load_position()

    def update_animation(self):
        # A külső célkereszt lassan forog az egyik irányba, a belső ívek a másikba
        self.angle_radar = (self.angle_radar + 0.5) % 360
        self.angle_inner = (self.angle_inner - 1.0) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        
        # --- Színek ---
        cyan = QColor(0, 255, 255, 200)
        cyan_faded = QColor(0, 255, 255, 60)
        white = QColor(230, 255, 255, 240)
        
        # A koordinátarendszer áthelyezése a widget közepére
        painter.translate(center)
        
        # --- Külső forgó célkereszt ---
        painter.save()
        painter.rotate(self.angle_radar)
        
        pen_crosshair = QPen(cyan, 2)
        painter.setPen(pen_crosshair)
        
        # 4 darab célkereszt vonal és ívek rajzolása
        for i in range(4):
            painter.drawLine(85, 0, 115, 0)
            painter.drawArc(-115, -115, 230, 230, 10 * 16, 25 * 16)
            painter.rotate(90)
            
        painter.restore()

        # --- Belső ellentétesen forgó szaggatott gyűrű ---
        painter.save()
        painter.rotate(self.angle_inner)
        pen_inner = QPen(cyan, 1.5)
        painter.setPen(pen_inner)
        
        for i in range(8):
            painter.drawArc(-75, -75, 150, 150, (i * 45) * 16, 20 * 16)
        painter.restore()

        # --- Statikus háttérkör ---
        pen_bg = QPen(cyan_faded, 1)
        painter.setPen(pen_bg)
        painter.drawEllipse(-100, -100, 200, 200)

        # --- Digitális Kijelző (Idő és Dátum) ---
        current_time = QTime.currentTime().toString("HH:mm:ss")
        current_date = QDate.currentDate().toString("yyyy.MM.dd")
        
        # Idő (Nagy betűtípus)
        font_time = QFont("Consolas", 18, QFont.Weight.Bold)
        painter.setFont(font_time)
        painter.setPen(white)
        
        fm_time = painter.fontMetrics()
        time_width = fm_time.horizontalAdvance(current_time)
        # Középre igazítás (x eltolás a szöveg szélességének fele, y eltolás picit lefelé)
        painter.drawText(int(-time_width / 2), 8, current_time)
        
        # Dátum (Kisebb betűtípus, felül)
        font_date = QFont("Consolas", 10, QFont.Weight.Bold)
        painter.setFont(font_date)
        painter.setPen(cyan)
        
        fm_date = painter.fontMetrics()
        date_width = fm_date.horizontalAdvance(current_date)
        painter.drawText(int(-date_width / 2), -22, current_date)
        
        # Alsó statikus dekorációs szöveg
        font_small = QFont("Consolas", 7, QFont.Weight.Bold)
        painter.setFont(font_small)
        painter.setPen(cyan_faded)
        painter.drawText(-22, 35, "SYS.CHRONO")

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
    widget = JarvisClockWidget()
    widget.show()
    sys.exit(app.exec())