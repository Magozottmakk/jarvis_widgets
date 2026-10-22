import sys
import json
import os
import urllib.request
import urllib.error
import ssl
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath

CONFIG_FILE = "jarvis_weather_config.json"

# Itt bármikor átírhatod a várost, amit monitorozni szeretnél!
TARGET_CITY = "Pecs"

class JarvisWeatherWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(340, 160) 
        
        self.city = "SCANNING..."
        self.temp = 0.0
        self.wind = 0.0
        self.status_text = "INITIALIZING SENSORS"
        self.has_data = False
        
        self.scan_angle = 0.0
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(20)
        
        self.api_timer = QTimer(self)
        self.api_timer.timeout.connect(self.fetch_weather_data)
        self.api_timer.start(15 * 60 * 1000) # 15 percenként frissít
        
        self.fetch_weather_data()
        
        self.drag_pos = None
        self.load_position()

    def update_animation(self):
        self.scan_angle = (self.scan_angle + 1.5) % 360
        self.update()

    def fetch_weather_data(self):
        try:
            # SSL ellenőrzés kikapcsolása
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            # A wttr.in szolgáltatás közvetlen hívása a beállított várossal
            # Szóközök cseréje URL kompatibilis formátumra
            safe_city = TARGET_CITY.replace(" ", "%20")
            url = f"https://wttr.in/{safe_city}?format=j1"
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req, timeout=5.0, context=ctx) as response:
                data = json.loads(response.read().decode())
                current = data['current_condition'][0]
                
                self.city = TARGET_CITY.upper()
                self.temp = float(current['temp_C'])
                self.wind = float(current['windspeedKmph'])
                desc = current['weatherDesc'][0]['value'].lower()
                
                # Kulcsszavas fordítás Jarvis-nyelvre
                if any(x in desc for x in ["sunny", "clear"]): 
                    self.status_text = "OPTIKAI TISZTASÁG (DERÜLT)"
                elif any(x in desc for x in ["cloud", "overcast"]): 
                    self.status_text = "RÉSZLEGES TAKARÁS (FELHŐS)"
                elif any(x in desc for x in ["fog", "mist"]): 
                    self.status_text = "LÁTHATÓSÁG CSÖKKENT (KÖD)"
                elif any(x in desc for x in ["rain", "drizzle", "shower"]): 
                    self.status_text = "CSAPADÉK ÉSZLELVE (ESŐ)"
                elif any(x in desc for x in ["snow", "ice"]): 
                    self.status_text = "SZILÁRD CSAPADÉK (HÓ)"
                elif any(x in desc for x in ["thunder", "storm"]): 
                    self.status_text = "ELEKTROMOS VIHAR RENDSZER"
                else: 
                    # Ha ismeretlen, kiírja az eredeti angol státuszt
                    self.status_text = f"ÁLLAPOT: {desc.upper()}"
                    
                self.has_data = True
                
        except urllib.error.URLError as e:
            self.city = "NET_ERROR"
            err_msg = str(e.reason)[:30].upper()
            self.status_text = f"ERR: {err_msg}"
            self.has_data = False
        except Exception as e:
            self.city = "SYS_ERROR"
            err_msg = str(e)[:30].upper()
            self.status_text = f"ERR: {err_msg}"
            self.has_data = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cyan_glow = QColor(0, 255, 255, 200)
        cyan_faded = QColor(0, 255, 255, 60)
        error_color = QColor(255, 100, 100, 255) 
        
        # UI Keret
        painter.setPen(QPen(cyan_faded, 1))
        painter.drawLine(10, 10, 30, 10)
        painter.drawLine(10, 10, 10, 30)
        painter.drawLine(10, h-10, w-10, h-10)
        painter.drawLine(w-10, h-30, w-10, h-10)
        
        # Animált szenzor ikon
        center_x, center_y = 50, h // 2
        
        painter.setPen(QPen(error_color if not self.has_data and self.city != "SCANNING..." else cyan_glow, 1.5))
        painter.drawEllipse(center_x - 30, center_y - 30, 60, 60)
        painter.setPen(QPen(cyan_faded, 1))
        painter.drawEllipse(center_x - 22, center_y - 22, 44, 44)
        
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.scan_angle)
        
        triangle = QPainterPath()
        triangle.moveTo(0, -15)
        triangle.lineTo(13, 10)
        triangle.lineTo(-13, 10)
        triangle.closeSubpath()
        
        painter.setPen(QPen(error_color if not self.has_data and self.city != "SCANNING..." else cyan_glow, 2))
        painter.setBrush(QColor(255, 0, 0, 40) if not self.has_data and self.city != "SCANNING..." else QColor(0, 255, 255, 40))
        painter.drawPath(triangle)
        painter.restore()

        # Adatpanelek
        font_large = QFont("Consolas", 18, QFont.Weight.Bold)
        font_medium = QFont("Consolas", 10, QFont.Weight.Bold)
        font_small = QFont("Consolas", 8, QFont.Weight.Normal)
        
        text_start_x = 100
        
        if self.has_data:
            painter.setFont(font_medium)
            painter.setPen(QColor(220, 255, 255, 255))
            painter.drawText(text_start_x, 35, f"LOC: {self.city}")
            
            painter.setFont(font_large)
            painter.setPen(cyan_glow)
            painter.drawText(text_start_x, 70, f"{self.temp} °C")
            
            painter.setFont(font_small)
            painter.setPen(QColor(220, 255, 255, 180))
            painter.drawText(text_start_x + 100, 68, f"WIND: {self.wind} km/h")
            
            painter.setFont(font_medium)
            painter.setPen(QColor(0, 255, 255, 220))
            painter.drawText(text_start_x, 105, self.status_text)
            
            painter.setPen(QPen(cyan_glow, 2))
            painter.drawLine(text_start_x, 115, w - 20, 115)
            
        else:
            painter.setFont(font_medium)
            painter.setPen(error_color if self.city in ["NET_ERROR", "SYS_ERROR"] else cyan_glow)
            painter.drawText(text_start_x, 50, f"LOC: {self.city}")
            painter.drawText(text_start_x, 80, self.status_text)

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
    widget = JarvisWeatherWidget()
    widget.show()
    sys.exit(app.exec())