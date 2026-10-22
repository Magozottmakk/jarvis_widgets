import sys
import json
import os
import random
import math
from PyQt6.QtWidgets import QApplication, QWidget, QSizeGrip
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath

# Hangkezelő modulok betöltése (Hibakezeléssel)
try:
    import pyaudio
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

CONFIG_FILE = "jarvis_audio_config.json"

class JarvisAudioWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(400, 150)
        
        self.grip = QSizeGrip(self)
        self.grip.setStyleSheet("background: transparent;")
        
        # Sávok beállításai
        self.num_bars = 32
        self.bars = [0.0] * self.num_bars
        self.peaks = [0.0] * self.num_bars # A leeső "csúcs" pöttyök
        
        # Audio Stream inicializálása
        self.p = None
        self.stream = None
        if AUDIO_AVAILABLE:
            try:
                self.p = pyaudio.PyAudio()
                # Megpróbáljuk megnyitni az alapértelmezett bemenetet (Mikrofon vagy Stereo Mix)
                self.stream = self.p.open(format=pyaudio.paInt16,
                                          channels=1,
                                          rate=44100,
                                          input=True,
                                          frames_per_buffer=1024)
            except Exception as e:
                print(f"Audio hiba: {e}")
                self.stream = None
                
        # Időzítő a kijelző frissítéséhez (~60 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_visualizer)
        self.anim_timer.start(16)
        
        self.drag_pos = None
        self.load_position()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.grip.resize(20, 20)
        self.grip.move(self.width() - 20, self.height() - 20)

    def update_visualizer(self):
        if self.stream is not None:
            try:
                # Olvasunk a hangkártyáról (nem blokkoló módon)
                data = self.stream.read(1024, exception_on_overflow=False)
                # Számmá alakítjuk a nyers adatot
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Fourier transzformáció (FFT) a frekvenciák kinyeréséhez
                fft_data = np.abs(np.fft.fft(audio_data))[:512]
                
                # Beosztjuk a kapott frekvenciákat a sávjainkba
                chunk_size = len(fft_data) // self.num_bars
                for i in range(self.num_bars):
                    # Átlagoljuk az adott frekvenciasáv erejét
                    band_power = np.mean(fft_data[i*chunk_size : (i+1)*chunk_size])
                    # Skálázzuk, hogy szépen mutasson (0-100 közötti értékre)
                    target_height = min(100.0, band_power / 10000.0 * 100.0)
                    
                    # Sima átmenet (Simulás)
                    self.bars[i] += (target_height - self.bars[i]) * 0.3
                    
            except Exception:
                pass
        else:
            # SZIMULÁCIÓS MÓD (Ha nincs mikrofon vagy hiba volt)
            for i in range(self.num_bars):
                # Véletlenszerű lüktetés szimulálása
                target = random.uniform(5, 95) if random.random() > 0.8 else max(5, self.bars[i] - 5)
                self.bars[i] += (target - self.bars[i]) * 0.2

        # Csúcs-pöttyök (Peaks) fizikája - lassan esnek lefelé
        for i in range(self.num_bars):
            if self.bars[i] > self.peaks[i]:
                self.peaks[i] = self.bars[i]
            else:
                self.peaks[i] = max(0, self.peaks[i] - 1.5) # Zuhanás sebessége

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cyan_glow = QColor(0, 255, 255, 220)
        cyan_faded = QColor(0, 255, 255, 40)
        white_peak = QColor(255, 255, 255, 255)
        
        # --- UI Keret ---
        painter.setPen(QPen(cyan_faded, 1))
        painter.drawLine(10, 10, 30, 10); painter.drawLine(10, 10, 10, 30)
        painter.drawLine(10, h-10, w-10, h-10); painter.drawLine(w-10, h-30, w-10, h-10)
        
        # Felirat
        font = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(0, 255, 255, 150))
        status = "ACTIVE" if self.stream else "SIMULATION MODE"
        painter.drawText(15, 20, f"AUDIO SPECTRUM UPLINK // {status}")
        
        # --- Spektrumanalizátor rajzolása ---
        # Sávok szélessége és helye a kereten belül
        margin_x = 20
        margin_y = 35
        graph_w = w - (margin_x * 2)
        graph_h = h - margin_y - 15
        
        bar_w = (graph_w / self.num_bars) - 2 # 2 pixel rés a sávok között
        
        for i in range(self.num_bars):
            x = margin_x + i * (bar_w + 2)
            
            # Sáv magassága (0 és graph_h között)
            bar_height = (self.bars[i] / 100.0) * graph_h
            y = margin_y + graph_h - bar_height
            
            # Maga a sáv
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(cyan_glow)
            painter.drawRect(int(x), int(y), int(bar_w), int(bar_height))
            
            # Leeső "Csúcs" (Peak) pötty
            peak_height = (self.peaks[i] / 100.0) * graph_h
            peak_y = margin_y + graph_h - peak_height
            
            painter.setBrush(white_peak)
            painter.drawRect(int(x), int(peak_y - 2), int(bar_w), 2)
            
        # Átméretező fogantyú (Jobb alsó sarok)
        painter.setPen(QPen(cyan_glow, 2))
        painter.drawLine(w - 15, h - 5, w - 5, h - 5)
        painter.drawLine(w - 5, h - 15, w - 5, h - 5)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()
        elif event.button() == Qt.MouseButton.RightButton:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.p:
                self.p.terminate()
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
                    if 'w' in pos and 'h' in pos:
                        self.resize(pos['w'], pos['h'])
            except Exception:
                pass

    def save_position(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'x': self.pos().x(), 'y': self.pos().y(), 'w': self.width(), 'h': self.height()}, f)
        except Exception:
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = JarvisAudioWidget()
    widget.show()
    sys.exit(app.exec())