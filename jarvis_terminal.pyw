import sys
import json
import os
import psutil
import random
from collections import deque
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont

CONFIG_FILE = "jarvis_terminal_config.json"

class JarvisTerminalWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Hosszúkás ablak a kódoknak
        self.resize(380, 400)
        
        # Várakozási sor a szövegsoroknak (max 25 sor fér a képernyőre)
        self.max_lines = 25
        self.lines = deque(maxlen=self.max_lines)
        
        # Futó folyamatok listája
        self.process_list = []
        self.refresh_processes()
        
        # 1. Időzítő: A terminál pörgetése (gyors, pl. 120 ms)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.add_new_line)
        self.anim_timer.start(120)
        
        # 2. Időzítő: A valódi folyamatok frissítése (5 másodpercenként, hogy ne terhelje a gépet)
        self.proc_timer = QTimer(self)
        self.proc_timer.timeout.connect(self.refresh_processes)
        self.proc_timer.start(5000)
        
        self.drag_pos = None
        self.load_position()

    def refresh_processes(self):
        # Lekérjük az aktív folyamatokat, de csak a nevüket és a memóriájukat
        try:
            self.process_list = [
                p.info for p in psutil.process_iter(['pid', 'name', 'memory_info'])
            ]
        except Exception:
            pass

    def add_new_line(self):
        # Ha valamiért üres a lista, generálunk kamu adatot
        if not self.process_list:
            proc_name = "SYS_IDLE"
            pid = "0000"
            mem = 0.0
        else:
            # Véletlenszerűen kiválasztunk egy futó folyamatot a listából
            proc = random.choice(self.process_list)
            proc_name = str(proc['name'])[:15].upper() # Maximum 15 karakter
            pid = str(proc['pid'])
            
            # Memória MB-ban
            mem = 0.0
            if proc.get('memory_info'):
                mem = proc['memory_info'].rss / 1024 / 1024

        # Véletlenszerű Hexadecimális memóriacím generálása a sci-fi hatáshoz
        hex_addr = f"0x{random.randint(0x100000, 0xFFFFFF):06X}"
        
        # Állapot kód (többnyire OK, néha SCAN vagy WAIT)
        status = random.choices(["[ OK ]", "[WAIT]", "[SCAN]", "[READ]"], weights=[70, 10, 10, 10])[0]
        
        # A formázott sor összeállítása
        # Pl.: 0xFA39C2 | CHROME.EXE    | PID:4512 | 145.2 MB [ OK ]
        new_line = f"{hex_addr} | {proc_name:<15} | PID:{pid:<5} | {mem:>6.1f} MB {status}"
        
        self.lines.append(new_line)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        #painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # Finom háttér a jobb olvashatóságért
        painter.setBrush(QColor(0, 20, 30, 80))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(0, 0, w, h)
        
        # Vékony keret és dekoráció
        painter.setPen(QPen(QColor(0, 255, 255, 100), 1))
        painter.drawRect(0, 0, w-1, h-1)
        
        # Sarok-célkeresztek
        painter.drawLine(0, 10, 10, 10); painter.drawLine(10, 0, 10, 10)
        painter.drawLine(w-10, 10, w, 10); painter.drawLine(w-10, 0, w-10, 10)
        
        # Szöveg renderelése
        font = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(font)
        
        line_height = 15
        start_y = 20
        
        for i, line in enumerate(self.lines):
            # A régebbi sorok halványabbak, a legújabb a legfényesebb
            alpha = int(50 + (205 * (i / self.max_lines)))
            
            # Néha véletlenszerűen vörösre vált egy-egy sor (hibaszimuláció)
            if "[WAIT]" in line:
                color = QColor(255, 100, 0, alpha) # Narancs
            else:
                color = QColor(0, 255, 255, alpha) # Cián
                
            painter.setPen(color)
            painter.drawText(15, start_y + (i * line_height), line)

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
    widget = JarvisTerminalWidget()
    widget.show()
    sys.exit(app.exec())