"""
Demo script for Newsletter Dialog
Shows how to use the NewsletterDialog with mock data
"""

import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

# Add the project path
sys.path.insert(0, '/Users/sci_coderamalamicia/PROJECTS/tech_news_scraper')

from gui_qt.theme import apply_theme, COLORS
from gui_qt.dialogs.newsletter_dialog import NewsletterDialog, show_newsletter_dialog


def create_mock_articles():
    """Create mock articles for demonstration"""
    return [
        {
            'id': '1',
            'title': 'OpenAI Releases GPT-5 with Revolutionary Multimodal Capabilities',
            'source': 'TechCrunch',
            'url': 'https://techcrunch.com/openai-gpt5',
            'category': 'AI/ML',
            'tech_score': 9.5,
            'summary': 'OpenAI has announced GPT-5, featuring unprecedented multimodal understanding across text, images, audio, and video with near-human reasoning capabilities.'
        },
        {
            'id': '2',
            'title': 'Google Cloud Launches New AI-Powered DevOps Suite',
            'source': 'The Verge',
            'url': 'https://theverge.com/google-cloud-devops',
            'category': 'Cloud',
            'tech_score': 8.7,
            'summary': 'Google Cloud introduces a comprehensive AI-powered DevOps platform that automates CI/CD pipelines and provides intelligent incident response.'
        },
        {
            'id': '3',
            'title': 'Critical Kubernetes Vulnerability Patched: Update Now',
            'source': 'Ars Technica',
            'url': 'https://arstechnica.com/kubernetes-cve',
            'category': 'Security',
            'tech_score': 9.8,
            'summary': 'A critical remote code execution vulnerability in Kubernetes has been discovered and patched. All cluster administrators should update immediately.'
        },
        {
            'id': '4',
            'title': 'Rust Adoption in Enterprise Reaches New Heights',
            'source': 'InfoWorld',
            'url': 'https://infoworld.com/rust-enterprise',
            'category': 'Programming',
            'tech_score': 7.5,
            'summary': 'Major enterprises including Microsoft, Amazon, and Google report significant increases in Rust adoption for systems programming and performance-critical applications.'
        },
        {
            'id': '5',
            'title': 'Quantum Computing Breakthrough: 1000-Qubit Processor Unveiled',
            'source': 'Wired',
            'url': 'https://wired.com/quantum-1000-qubit',
            'category': 'Quantum',
            'tech_score': 9.2,
            'summary': 'IBM has unveiled a 1000-qubit quantum processor, marking a significant milestone in the race toward practical quantum computing applications.'
        },
        {
            'id': '6',
            'title': 'New JavaScript Framework Promises 10x Performance Boost',
            'source': 'JavaScript Weekly',
            'url': 'https://javascriptweekly.com/new-framework',
            'category': 'Web Dev',
            'tech_score': 7.8,
            'summary': 'A new JavaScript framework claims to deliver 10x better performance than React through innovative virtual DOM diffing and compile-time optimizations.'
        },
        {
            'id': '7',
            'title': 'Major Data Breach Exposes 50M User Records',
            'source': 'Krebs on Security',
            'url': 'https://krebsonsecurity.com/data-breach',
            'category': 'Security',
            'tech_score': 8.9,
            'summary': 'A major social media platform has suffered a data breach affecting 50 million users, with personal information including emails and phone numbers leaked.'
        },
        {
            'id': '8',
            'title': 'Apple Silicon M4: Neural Engine Gets Major Upgrade',
            'source': 'MacRumors',
            'url': 'https://macrumors.com/m4-neural',
            'category': 'Hardware',
            'tech_score': 8.4,
            'summary': 'The new M4 chip features a significantly enhanced Neural Engine capable of 38 trillion operations per second, enabling on-device AI features.'
        }
    ]


class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Newsletter Dialog Demo")
        self.setMinimumSize(400, 200)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Info label
        info = QLabel("Click below to open the Newsletter Studio")
        info.setStyleSheet(f"color: {COLORS.comment}; font-size: 14px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # Open dialog button
        open_btn = QPushButton("📧 Open Newsletter Studio")
        open_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS.blue}, stop:1 {COLORS.cyan});
                color: {COLORS.black};
                border: none;
                border-radius: 8px;
                padding: 16px 32px;
                font-weight: bold;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS.bright_blue}, stop:1 {COLORS.bright_cyan});
            }}
        """)
        open_btn.clicked.connect(self.open_newsletter_dialog)
        layout.addWidget(open_btn)
        
        # Modal dialog button
        modal_btn = QPushButton("📧 Open as Modal Dialog")
        modal_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.bg_highlight};
                color: {COLORS.fg};
                border: 2px solid {COLORS.terminal_black};
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 500;
                font-size: 14px;
            }}
            QPushButton:hover {{
                border-color: {COLORS.cyan};
                color: {COLORS.cyan};
            }}
        """)
        modal_btn.clicked.connect(self.open_modal_dialog)
        layout.addWidget(modal_btn)
        
        layout.addStretch()
        
    def open_newsletter_dialog(self):
        """Open the newsletter dialog non-modally"""
        articles = create_mock_articles()
        self.dialog = NewsletterDialog(self, articles=articles)
        self.dialog.show()
        
    def open_modal_dialog(self):
        """Open the newsletter dialog as a modal"""
        articles = create_mock_articles()
        show_newsletter_dialog(self, articles=articles)


def main():
    app = QApplication(sys.argv)
    
    # Apply Tokyo Night theme
    apply_theme(app)
    
    # Create and show demo window
    window = DemoWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    from PyQt6.QtWidgets import QLabel
    main()
