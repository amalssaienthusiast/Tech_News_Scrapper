# Tech News Scraper

An advanced AI-powered tech news scraper with web discovery capabilities.

## Features

- Real-time web discovery of tech news sources
- AI-powered source verification
- Automatic expansion of news sources
- Enhanced scraping from RSS feeds and direct web pages
- AI summarization of articles
- Semantic search functionality
- User-friendly GUI interface

## Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python main.py` (CLI) or `python gui/app.py` (GUI)

## Usage

### CLI Mode
Run `python main.py` to start the scraper in CLI mode with automatic periodic scraping.

### GUI Mode
Run `python gui/app.py` to start the application with a graphical interface.

## Configuration

Configuration settings can be modified in `config/settings.py`.

## Project Structure

- `config/`: Configuration settings
- `src/`: Core application modules
- `gui/`: GUI application
- `tests/`: Unit tests
- `data/`: Storage for scraped articles
- `logs/`: Application logs
- `cache/`: Temporary cache files
- `discovered_sources/`: Discovered news sources

## License

This project is licensed under the MIT License.
