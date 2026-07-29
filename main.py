from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from database import get_all_flohmaerkte, init_db
from datetime import datetime, date
import os

app = FastAPI(title="Flohmarkt-Radar API")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/api/flohmaerkte")
def get_flohmaerkte(
    plz: str = None,
    city: str = None,
    date_from: str = None,
    date_to: str = None,
    today: bool = False,
    weekend: bool = False
):
    all_items = get_all_flohmaerkte()

    today_date = date.today()

    results = []
    for item in all_items:
        match = True

        if plz and item.get('plz'):
            if not item['plz'].startswith(plz):
                match = False

        if city and item.get('city'):
            if city.lower() not in item['city'].lower():
                match = False

        if today and item.get('date_start'):
            try:
                ds = datetime.strptime(item['date_start'], '%Y-%m-%d').date()
                if ds != today_date:
                    match = False
            except (ValueError, TypeError):
                pass

        if today and not item.get('date_start'):
            match = False

        if match:
            results.append(item)

    geo_json = {
        "type": "FeatureCollection",
        "features": []
    }

    seen = set()
    for item in results:
        if item['lat'] and item['lng']:
            key = item['id']
            if key not in seen:
                seen.add(key)
                geo_json["features"].append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [item['lng'], item['lat']]
                    },
                    "properties": {
                        "id": item['id'],
                        "name": item['name'],
                        "plz": item['plz'],
                        "city": item['city'],
                        "bundesland": item['bundesland'],
                        "date_start": item.get('date_start'),
                        "date_end": item.get('date_end'),
                        "time_start": item.get('time_start'),
                        "time_end": item.get('time_end'),
                        "url": item.get('source_url'),
                    }
                })

    return geo_json


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__), "index.html"), encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
