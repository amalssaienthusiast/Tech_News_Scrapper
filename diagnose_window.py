"""
Diagnostic script to check PyQt6 window display issues
"""
import sys
import platform
sys.path.insert(0, '.')

from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QMessageBox
from PyQt6.QtCore import Qt

from gui_qt.theme import apply_theme, COLORS

class DiagnosticWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tech News Scraper - Diagnostic")
        self.setMinimumSize(600, 400)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Status label
        self.status_label = QLabel("🔍 Running diagnostics...")
        self.status_label.setStyleSheet(f"font-size: 18px; color: {COLORS.cyan}; padding: 20px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Info label
        info = QLabel(f"Platform: {platform.system()}<br>Python: {sys.version[:50]}...")
        info.setStyleSheet(f"color: {COLORS.fg}; padding: 10px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # Test button
        btn = QPushButton("Test Button")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.green};
                color: {COLORS.black};
                padding: 15px 30px;
                font-size: 16px;
                border-radius: 8px;
            }}
        """)
        btn.clicked.connect(self.on_test)
        layout.addWidget(btn)
        
        # Force show and activate
        self.show()
        self.raise_()
        self.activateWindow()
        
        self.status_label.setText("✅ Window should be visible!<br>If you can't see it, check:<br>- Is it behind other windows?<br>- Is the app in the Dock?<br>- Try clicking the Dock icon")
    
    def on_test(self):
        QMessageBox.information(self, "Test", "Button clicked successfully!")

def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    
    window = DiagnosticWindow()
    
    # macOS specific activation
    if platform.system() == "Darwin":
        # Try to activate the app
        try:
            from Cocoa import NSApplication, NSApp
            NSApp.activateIgnoringOtherApps_(True)
        except ImportError:
            pass
        
        # Alternative method
        window.setWindowFlags(
            window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )
        window.show()
        window.raise_()
        window.activateWindow()
    
    print("Window created and shown")
    print("If you don't see a window, check:")
    print("1. Look in the Dock for 'Python' or 'Tech News Scraper'")
    print("2. Check if window is minimized")
    print("3. Check if window is behind other windows")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
