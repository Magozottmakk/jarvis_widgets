import sys
import os
import importlib.util
import urllib.request
import json
import ssl
import time
import random
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

# Beépített, villámgyors CPU és RAM olvasó
import psutil 

WIDGETS_TO_LOAD = [
    ("jarvis_system_widget.pyw", "JarvisSystemWidget"),
    ("jarvis_network.pyw", "JarvisNetworkWidget"),
    ("jarvis_clock.pyw", "JarvisClockWidget"),
    ("jarvis_folder.pyw", "JarvisFolderWidget"),
    ("jarvis_terminal.pyw", "JarvisTerminalWidget"),
    ("jarvis_radar.pyw", "JarvisRadarWidget"),
    ("jarvis_3d_core.pyw", "Jarvis3DWidget"),
    ("jarvis_weather.pyw", "JarvisWeatherWidget"),
    ("jarvis_audio.pyw", "JarvisAudioWidget")
]

# Egy kamu adat-osztály a Terminál számára, hogy ne terhelje a gépet a valódi lekérdezés
class DummyMemory:
    def __init__(self, rss):
        self.rss = rss

JARVIS_PROCESSES = [
    {'name': 'J.A.R.V.I.S_CORE', 'pid': 1024, 'memory_info': DummyMemory(256000000)},
    {'name': 'NEURAL_NET.EXE', 'pid': 4048, 'memory_info': DummyMemory(1024000000)},
    {'name': 'UPLINK_RELAY', 'pid': 108, 'memory_info': DummyMemory(50000000)},
    {'name': 'DEFENSE_GRID', 'pid': 256, 'memory_info': DummyMemory(400000000)},
    {'name': 'AUDIO_VIZ_SYS', 'pid': 512, 'memory_info': DummyMemory(15000000)},
    {'name': 'SAT_TRACKER', 'pid': 1138, 'memory_info': DummyMemory(85000000)},
    {'name': 'SYS_IDLE', 'pid': 0, 'memory_info': DummyMemory(4096)}
]

# --- 1. A HÁTTÉR ADATMAG (Nem fagyasztja a grafikát!) ---
class JarvisDataCore(QThread):
    sys_signal = pyqtSignal(float, float)      
    iss_signal = pyqtSignal(float, float)      
    weather_signal = pyqtSignal(float, float, str) 

    def run(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        loop_counter = 0
        while not self.isInterruptionRequested():
            
            # 1. CPU és RAM (Gyors, nem akaszt) - Fél másodpercenként
            if loop_counter % 5 == 0:
                try:
                    cpu = psutil.cpu_percent()
                    ram = psutil.virtual_memory().percent
                    self.sys_signal.emit(cpu, ram)
                except: pass

            # 2. ISS Radar - 5 másodpercenként
            if loop_counter % 50 == 0:
                try:
                    req = urllib.request.Request("http://api.open-notify.org/iss-now.json", headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=2.0, context=ctx) as response:
                        data = json.loads(response.read().decode())
                        self.iss_signal.emit(float(data['iss_position']['latitude']), float(data['iss_position']['longitude']))
                except: pass

            # 3. Időjárás - 10 percenként
            if loop_counter == 0 or loop_counter % 6000 == 0:
                try:
                    req = urllib.request.Request("https://wttr.in/Frankfurt?format=j1", headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5.0, context=ctx) as response:
                        data = json.loads(response.read().decode())
                        current = data['current_condition'][0]
                        temp = float(current['temp_C'])
                        wind = float(current['windspeedKmph'])
                        desc = current['weatherDesc'][0]['value'].lower()
                        
                        status = "ÁLLAPOT NORMÁL"
                        if any(x in desc for x in ["sunny", "clear"]): status = "OPTIKAI TISZTASÁG (DERÜLT)"
                        elif any(x in desc for x in ["cloud", "overcast"]): status = "RÉSZLEGES TAKARÁS (FELHŐS)"
                        elif any(x in desc for x in ["rain", "drizzle"]): status = "CSAPADÉK ÉSZLELVE (ESŐ)"
                        elif any(x in desc for x in ["snow", "ice"]): status = "SZILÁRD CSAPADÉK (HÓ)"
                        
                        self.weather_signal.emit(temp, wind, status)
                except: pass

            time.sleep(0.1)
            loop_counter += 1

def load_pyw_module(module_name, file_path):
    if not os.path.exists(file_path): return None
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class JarvisMasterOS:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False) 
        
        self.active_widgets = []
        self.init_tray_icon()
        
        # Adatmag indítása
        self.data_core = JarvisDataCore()
        self.data_core.sys_signal.connect(self.update_sys_data)
        self.data_core.iss_signal.connect(self.update_iss_data)
        self.data_core.weather_signal.connect(self.update_weather_data)
        self.data_core.start()
        
        self.boot_system()
        
        self.tick_counter = 0
        self.master_timer = QTimer()
        self.master_timer.timeout.connect(self.master_clock_tick)
        self.master_timer.start(33) # Fix 30 FPS, akadás nélkül!

    def init_tray_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(0, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()
        
        self.tray = QSystemTrayIcon(QIcon(pixmap), self.app)
        self.tray.setToolTip("J.A.R.V.I.S. OS (No Lag Version)")
        
        menu = QMenu()
        show_act = menu.addAction("👁 Mutat")
        hide_act = menu.addAction("👻 Elrejt")
        menu.addSeparator()
        exit_act = menu.addAction("🛑 Leállít")
        
        show_act.triggered.connect(self.show_all)
        hide_act.triggered.connect(self.hide_all)
        exit_act.triggered.connect(self.shutdown)
        self.tray.setContextMenu(menu)
        self.tray.show()

    def boot_system(self):
        for file_name, class_name in WIDGETS_TO_LOAD:
            mod = load_pyw_module(class_name, file_name)
            if mod and hasattr(mod, class_name):
                try:
                    WidgetClass = getattr(mod, class_name)
                    w = WidgetClass()
                    
                    # Belső időzítők és a laggolást okozó funkciók KIKAPCSOLÁSA
                    if hasattr(w, 'anim_timer'): w.anim_timer.stop()
                    if hasattr(w, 'stats_timer'): w.stats_timer.stop()
                    if hasattr(w, 'api_timer'): w.api_timer.stop()
                    if hasattr(w, 'proc_timer'): w.proc_timer.stop()
                    
                    # A Terminál megkapja a "kamu" listát, hogy ne terhelje a CPU-t
                    if class_name == "JarvisTerminalWidget":
                        w.process_list = JARVIS_PROCESSES
                    
                    self.active_widgets.append(w)
                    w.show()
                except Exception as e:
                    pass

    # --- INJEKTÁLÁS ---
    def update_sys_data(self, cpu, ram):
        for w in self.active_widgets:
            if w.__class__.__name__ == "JarvisSystemWidget":
                w.cpu_usage = cpu; w.ram_usage = ram
            elif w.__class__.__name__ == "Jarvis3DWidget":
                w.cpu_usage = cpu

    def update_iss_data(self, lat, lon):
        for w in self.active_widgets:
            if w.__class__.__name__ == "JarvisRadarWidget":
                w.iss_lat = lat; w.iss_lon = lon; w.has_data = True

    def update_weather_data(self, temp, wind, status):
        for w in self.active_widgets:
            if w.__class__.__name__ == "JarvisWeatherWidget":
                w.city = "FRANKFURT"; w.temp = temp; w.wind = wind
                w.status_text = status; w.has_data = True

    # --- GRAFIKA ---
    def master_clock_tick(self):
        self.tick_counter += 1
        for w in self.active_widgets:
            if not w.isVisible(): continue
            class_name = w.__class__.__name__
            
            if class_name in ["JarvisSystemWidget", "JarvisClockWidget", "JarvisRadarWidget", "Jarvis3DWidget", "JarvisFolderWidget", "JarvisWeatherWidget"]:
                w.update_animation()
            elif class_name == "JarvisAudioWidget":
                w.update_visualizer()
            elif class_name == "JarvisTerminalWidget" and self.tick_counter % 4 == 0:
                w.add_new_line()
            
            w.update()

    def show_all(self):
        for w in self.active_widgets: w.show()

    def hide_all(self):
        for w in self.active_widgets: w.hide()

    def shutdown(self):
        self.master_timer.stop()
        self.data_core.requestInterruption()
        self.data_core.wait()
        for w in self.active_widgets:
            if w.__class__.__name__ == "JarvisAudioWidget" and hasattr(w, 'stream'):
                if w.stream: w.stream.stop_stream(); w.stream.close()
                if w.p: w.p.terminate()
            w.close()
        self.app.quit()

if __name__ == '__main__':
    os_core = JarvisMasterOS()
    sys.exit(os_core.app.exec())