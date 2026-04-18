"""
Quick test to check article display in FeedPanel
"""
import sys
sys.path.insert(0, '.')

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer
from gui_qt.panels.feed_panel import FeedPanel
from gui_qt.theme import apply_theme
from src.database import get_database

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FeedPanel Test")
        self.setMinimumSize(800, 600)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Create feed panel
        self.feed_panel = FeedPanel()
        layout.addWidget(self.feed_panel)
        
        # Load articles after a short delay
        QTimer.singleShot(500, self.load_articles)
    
    def load_articles(self):
        db = get_database()
        articles = db.get_all_articles()
        print(f"Loading {len(articles)} articles...")
        self.feed_panel.set_articles(articles)
        print(f"Articles passed to FeedPanel")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_theme(app)
    
    window = TestWindow()
    window.show()
    
    print("Window shown - articles should load in 500ms")
    sys.exit(app.exec())
