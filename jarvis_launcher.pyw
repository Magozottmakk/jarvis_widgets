import sys
import json
import os
from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QFileDialog, QMenu
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QAction

POS_CONFIG = "jarvis_launcher_pos.json"
APPS_CONFIG = "jarvis_apps.json"

DEFAULT_APPS = [
    {"name": "CORE", "path": "jarvis_system_widget.pyw"},
    {"name": "UPLINK", "path": "jarvis_network.pyw"},
    {"name": "CHRONO", "path": "jarvis_clock.pyw"},
    {"name": "FILES", "path": "jarvis_folder.pyw"}
]

class JarvisButton(QWidget):
    def __init__(self, app_data, index, launcher_parent):
        super().__init__(launcher_parent)
        self.app_data = app_data
        self.index = index
        self.launcher = launcher_parent
        
        self.name = app_data['name']
        self.path = app_data['path']
        self.setFixedSize(130, 45)
        self.setMouseTracking(True)
        
        self.hover_anim = 0.0
        self.is_hovered = False
        
    def enterEvent(self, event):
        self.is_hovered = True
        
    def leaveEvent(self, event):
        self.is_hovered = False
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            try:
                os.startfile(self.path)
            except Exception as e:
                print(f"Hiba az indításkor: {e}")

    # Gomb specifikus jobb-klikk menü (Átrendezés és Törlés)
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # Stílus a menühöz (Sötét, Jarvis stílus)
        menu.setStyleSheet("""
            QMenu { background-color: rgba(0, 40, 60, 220); color: #00ffff; border: 1px solid #00ffff; }
            QMenu::item:selected { background-color: rgba(0, 255, 255, 50); }
        """)
        
        move_left_act = QAction("⬅ Mozgatás Balra", self)
        move_right_act = QAction("➡ Mozgatás Jobbra", self)
        remove_act = QAction("✖ Törlés", self)
        
        move_left_act.triggered.connect(lambda: self.launcher.move_app(self.index, -1))
        move_right_act.triggered.connect(lambda: self.launcher.move_app(self.index, 1))
        remove_act.triggered.connect(lambda: self.launcher.remove_app(self.index))
        
        # Csak akkor engedélyezzük a mozgatást, ha van értelme
        if self.index > 0:
            menu.addAction(move_left_act)
        if self.index < len(self.launcher.apps) - 1:
            menu.addAction(move_right_act)
            
        menu.addSeparator()
        menu.addAction(remove_act)
        
        menu.exec(event.globalPos())

    def update_anim(self):
        if self.is_hovered and self.hover_anim < 1.0:
            self.hover_anim += 0.15
        elif not self.is_hovered and self.hover_anim > 0.0:
            self.hover_anim -= 0.15
        self.hover_anim = max(0.0, min(1.0, self.hover_anim))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        
        cyan_base = QColor(0, 255, 255, 30 + int(80 * self.hover_anim))
        cyan_glow = QColor(0, 255, 255, 200 + int(55 * self.hover_anim))
        
        path = QPainterPath()
        path.moveTo(15, 5)
        path.lineTo(w - 5, 5)
        path.lineTo(w - 15, h - 10)
        path.lineTo(5, h - 10)
        path.closeSubpath()
        
        painter.setBrush(cyan_base)
        painter.setPen(QPen(cyan_glow, 1))
        painter.drawPath(path)
        
        if self.hover_anim > 0.05:
            painter.setPen(QPen(cyan_glow, 3))
            line_w = (w - 20) * self.hover_anim
            painter.drawLine(10, h - 3, int(10 + line_w), h - 3)
        
        painter.setPen(QColor(220, 255, 255, 255))
        font = QFont("Consolas", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, -2, 0, -5), Qt.AlignmentFlag.AlignCenter, self.name)


class JarvisLauncher(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Engedélyezzük a Drag & Drop fájl fogadást
        self.setAcceptDrops(True)
        
        self.drag_pos = None
        self.buttons = []
        self.apps = []
        
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(30, 20, 30, 20)
        self.setLayout(self.main_layout)
        
        self.init_config()
        self.build_ui()
        self.load_position()
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_all_buttons)
        self.anim_timer.start(16)
        
    def init_config(self):
        if not os.path.exists(APPS_CONFIG):
            self.apps = DEFAULT_APPS.copy()
            self.save_apps()
        else:
            try:
                with open(APPS_CONFIG, 'r', encoding='utf-8') as f:
                    self.apps = json.load(f)
            except Exception:
                self.apps = DEFAULT_APPS.copy()
                
    def save_apps(self):
        with open(APPS_CONFIG, 'w', encoding='utf-8') as f:
            json.dump(self.apps, f, indent=4)
            
    def build_ui(self):
        # Régi gombok azonnali elrejtése és törlése a "szellemkép" elkerülése végett
        for i in reversed(range(self.main_layout.count())): 
            item = self.main_layout.takeAt(i)
            widget = item.widget()
            if widget is not None:
                widget.hide() # Ez a kulcs: azonnal eltünteti a képernyőről
                widget.deleteLater()
                
        self.buttons.clear()
        
        # Új gombok építése a lista alapján
        for index, app in enumerate(self.apps):
            btn = JarvisButton(app, index, self)
            self.buttons.append(btn)
            self.main_layout.addWidget(btn)
            
        self.adjustSize()
        self.repaint() # Kényszerített azonnali frissítés az átlátszó háttéren

    # --- Húzd és Dobd (Drag & Drop) Események ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            # Fájlnév kinyerése és Jarvis-osítása (Nagybetűs, kiterjesztés nélkül)
            base_name = os.path.basename(file_path).split('.')[0].upper()
            
            # Túl hosszú név levágása
            if len(base_name) > 12:
                base_name = base_name[:10] + ".."
                
            self.add_app(base_name, file_path)

    # --- Alkalmazás Menedzsment Logika ---
    def add_app(self, name, path):
        self.apps.append({"name": name, "path": path})
        self.save_apps()
        self.build_ui()
        
    def remove_app(self, index):
        if 0 <= index < len(self.apps):
            self.apps.pop(index)
            self.save_apps()
            self.build_ui()
            
    def move_app(self, index, direction):
        new_index = index + direction
        if 0 <= index < len(self.apps) and 0 <= new_index < len(self.apps):
            # Csere a listában
            self.apps[index], self.apps[new_index] = self.apps[new_index], self.apps[index]
            self.save_apps()
            self.build_ui()

    # --- Tálca Jobb-Klikk Menü (Tallózás és Kilépés) ---
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: rgba(0, 40, 60, 220); color: #00ffff; border: 1px solid #00ffff; }
            QMenu::item:selected { background-color: rgba(0, 255, 255, 50); }
        """)
        
        add_act = QAction("➕ Alkalmazás Hozzáadása (Tallózás)", self)
        exit_act = QAction("🛑 Rendszer Leállítása (Kilépés)", self)
        
        add_act.triggered.connect(self.browse_app)
        exit_act.triggered.connect(self.close)
        
        menu.addAction(add_act)
        menu.addSeparator()
        menu.addAction(exit_act)
        
        menu.exec(event.globalPos())

    def browse_app(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Alkalmazás Kiválasztása", "", "Minden fájl (*);;Futtatható fájlok (*.exe);;Python fájlok (*.pyw *.py)")
        if file_path:
            base_name = os.path.basename(file_path).split('.')[0].upper()
            if len(base_name) > 12:
                base_name = base_name[:10] + ".."
            self.add_app(base_name, file_path)

    def update_all_buttons(self):
        for btn in self.buttons:
            btn.update_anim()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.setPen(QPen(QColor(0, 255, 255, 120), 2))
        
        painter.drawLine(15, 10, 35, 10)
        painter.drawLine(15, 10, 15, h - 10)
        painter.drawLine(15, h - 10, 35, h - 10)
        
        painter.drawLine(w - 35, 10, w - 15, 10)
        painter.drawLine(w - 15, 10, w - 15, h - 10)
        painter.drawLine(w - 35, h - 10, w - 15, h - 10)

    # --- Ablak mozgatása ---
    def mousePressEvent(self, event):
        # A jobb klikket átadtuk a contextMenuEvent-nek, itt csak a mozgást kezeljük
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.pos() + delta)
            self.drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        self.save_position()

    def load_position(self):
        if os.path.exists(POS_CONFIG):
            try:
                with open(POS_CONFIG, 'r') as f:
                    pos = json.load(f)
                    self.move(pos['x'], pos['y'])
            except Exception:
                pass

    def save_position(self):
        try:
            with open(POS_CONFIG, 'w') as f:
                json.dump({'x': self.pos().x(), 'y': self.pos().y()}, f)
        except Exception:
            pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = JarvisLauncher()
    widget.show()
    sys.exit(app.exec())