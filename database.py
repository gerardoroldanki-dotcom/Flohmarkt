import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "flohmarkt.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS flohmaerkte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            plz TEXT,
            city TEXT,
            bundesland TEXT,
            lat REAL,
            lng REAL,
            source_url TEXT UNIQUE,
            source TEXT DEFAULT 'flohmarktkalender.com',
            last_seen DATE DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS termine (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flohmarkt_id INTEGER REFERENCES flohmaerkte(id),
            date_start DATE,
            date_end DATE,
            time_start TEXT,
            time_end TEXT,
            day_of_week TEXT,
            recurrence TEXT,
            UNIQUE(flohmarkt_id, date_start, time_start)
        );

        CREATE INDEX IF NOT EXISTS idx_termin_date ON termine(date_start);
        CREATE INDEX IF NOT EXISTS idx_flohmarkt_location ON flohmaerkte(lat, lng);
    """)
    conn.commit()
    conn.close()


def save_flohmarkt(name, plz, city, bundesland, lat, lng, source_url):
    conn = get_connection()
    conn.execute("""
        INSERT INTO flohmaerkte (name, plz, city, bundesland, lat, lng, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_url) DO UPDATE SET
            name=excluded.name, plz=excluded.plz, city=excluded.city,
            bundesland=excluded.bundesland, lat=excluded.lat, lng=excluded.lng,
            last_seen=date('now')
    """, (name, plz, city, bundesland, lat, lng, source_url))
    conn.commit()
    floh_id = conn.execute("SELECT id FROM flohmaerkte WHERE source_url = ?", (source_url,)).fetchone()[0]
    conn.close()
    return floh_id


def save_termin(flohmarkt_id, date_start, date_end, time_start, time_end, day_of_week, recurrence):
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO termine (flohmarkt_id, date_start, date_end, time_start, time_end, day_of_week, recurrence)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (flohmarkt_id, date_start, date_end, time_start, time_end, day_of_week, recurrence))
    conn.commit()
    conn.close()


def get_all_flohmaerkte():
    conn = get_connection()
    rows = conn.execute("""
        SELECT f.*, t.date_start, t.date_end, t.time_start, t.time_end, t.day_of_week, t.recurrence
        FROM flohmaerkte f
        LEFT JOIN termine t ON t.flohmarkt_id = f.id
        ORDER BY t.date_start
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
