# Flohmarkt Radar

Real-time flea market finder for Germany with map visualization.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/gerardoroldanki-dotcom/Flohmarkt.git
cd Flohmarkt

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
uvicorn main:app --host 0.0.0.0 --port 8765
```

Open http://localhost:8765 in your browser.

## Scraping new data

```bash
python scraper.py
```

The database (`flohmarkt.db`) comes pre-populated with 87 flea markets from flohmarkt-termine.org.
