import sys
import json
import os
import subprocess
import random
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath

CONFIG_FILE = "jarvis_folder_config.json"

class JarvisFolderWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Ablak beállítások
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(350, 200)
        
        # Animációs változók a 3 sávhoz
        self.bars = [50.0, 70.0, 30.0]
        self.targets = [50.0, 70.0, 30.0]
        
        # Időzítő az animációhoz
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(30) # ~30 FPS
        
        self.drag_pos = None
        self.load_position()

    def update_animation(self):
        # A sávok folyamatosan véletlenszerű célok felé mozognak (olvasás/írás szimuláció)
        for i in range(3):
            if abs(self.bars[i] - self.targets[i]) < 2:
                # Új célpont generálása (20% és 95% között)
                self.targets[i] = random.uniform(20, 95)
            
            # Sima átmenet a cél felé
            if self.bars[i] < self.targets[i]:
                self.bars[i] += 0.8
            else:
                self.bars[i] -= 0.8
                
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # Színek
        cyan_glow = QColor(0, 255, 255, 180)
        cyan_bright = QColor(150, 255, 255, 255)
        bg_color = QColor(0, 40, 60, 150) # Halvány sötétkék panel háttér
        
        # --- Csapott sarkú sci-fi panel rajzolása ---
        path = QPainterPath()
        path.moveTo(40, 10)         # Bal felső csapás kezdete
        path.lineTo(w - 10, 10)     # Jobb felső egyenes
        path.lineTo(w - 10, h - 40) # Jobb alsó csapás kezdete
        path.lineTo(w - 40, h - 10) # Jobb alsó csapás vége
        path.lineTo(10, h - 10)     # Bal alsó egyenes
        path.lineTo(10, 40)         # Bal felső csapás vége
        path.closeSubpath()
        
        # Háttér kitöltése
        painter.setBrush(bg_color)
        pen_border = QPen(cyan_glow, 2)
        painter.setPen(pen_border)
        painter.drawPath(path)
        
        # Dekoratív vonalak a panelen (mint a képen felül)
        painter.drawLine(w - 100, 10, w - 80, 0)
        painter.drawLine(w - 80, 0, w - 30, 0)

        # --- Szövegek és Sávok ---
        font = QFont("Consolas", 12, QFont.Weight.Bold)
        painter.setFont(font)
        
        labels = ["SYSTEM DIRECTORY", "SECURE ARCHIVES", "DATA UPLINK"]
        
        start_y = 45
        spacing = 50
        
        for i in range(3):
            # Szöveg
            painter.setPen(cyan_bright)
            painter.drawText(30, start_y + (i * spacing), labels[i])
            
            # Üres sáv kerete (háttér)
            bar_y = start_y + 10 + (i * spacing)
            bar_h = 6
            bar_max_w = w - 60
            
            painter.setPen(QPen(QColor(0, 255, 255, 50), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(30, bar_y, bar_max_w, bar_h)
            
            # Kitöltött animált sáv
            current_w = int((self.bars[i] / 100.0) * bar_max_w)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(cyan_glow)
            painter.drawRect(30, bar_y, current_w, bar_h)
            
            # Sáv végén lévő fényes "fej" (mint a képen a kis fehér vonal)
            painter.setBrush(cyan_bright)
            painter.drawRect(30 + current_w - 4, bar_y, 4, bar_h)

    # --- Interakciók: Mozgatás és Megnyitás ---
    
    def mouseDoubleClickEvent(self, event):
        # Dupla kattintásra megnyitja a Windows Fájlkezelőt
        if event.button() == Qt.MouseButton.LeftButton:
            subprocess.Popen("explorer")

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

    # --- Pozíció mentése és betöltése ---
    
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = JarvisFolderWidget()
    widget.show()
    sys.exit(app.exec())