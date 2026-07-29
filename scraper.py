import requests
import re
import time
from datetime import datetime, date
from bs4 import BeautifulSoup
from database import init_db, save_flohmarkt, save_termin

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

MONTH_MAP = {
    'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5, 'Juni': 6,
    'Juli': 7, 'August': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12,
    'Jan': 1, 'Feb': 2, 'Mär': 3, 'Apr': 4, 'Mai': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Okt': 10, 'Nov': 11, 'Dez': 12
}

DAY_MAP = {
    'Montag': 'Monday', 'Dienstag': 'Tuesday', 'Mittwoch': 'Wednesday',
    'Donnerstag': 'Thursday', 'Freitag': 'Friday', 'Samstag': 'Saturday', 'Sonntag': 'Sunday'
}


def parse_german_date(date_str):
    date_str = date_str.strip()
    date_str = re.sub(r'\s+', ' ', date_str)
    for de, en in DAY_MAP.items():
        date_str = date_str.replace(de, '')
    date_str = date_str.strip()
    try:
        return datetime.strptime(date_str, '%d.%m.%y').date()
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str, '%d.%m.%Y').date()
    except ValueError:
        pass
    return None


def geocode(plz, city):
    try:
        resp = session.get(
            'https://nominatim.openstreetmap.org/search',
            params={
                'q': f'{plz} {city}, Deutschland',
                'format': 'json',
                'limit': 1
            },
            headers={'User-Agent': 'FlohmarktRadar/1.0 (educational project)'}
        )
        if resp.status_code == 200 and resp.json():
            data = resp.json()[0]
            return float(data['lat']), float(data['lon'])
    except Exception as e:
        print(f'  Geocode error for {plz} {city}: {e}')
    return None, None


def scrape_list_page(page=1):
    resp = session.post(
        'https://www.flohmarktkalender.com/wp-admin/admin-ajax.php',
        data={'action': 'search_events', 'view_id': '1', 'em_search': '', 'page': str(page), 'scope': 'all'}
    )
    if resp.status_code != 200:
        print(f'  Page {page}: HTTP {resp.status_code}')
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    rows = soup.select('table tr')
    events = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 2:
            continue

        date_text = cols[0].get_text(strip=True)
        link = cols[1].find('a')
        if not link:
            continue

        name = link.get_text(strip=True)
        url = link.get('href', '')
        city_text = cols[1].find('i')
        location = city_text.get_text(strip=True) if city_text else ''
        state_links = cols[1].find_all('a', href=True)
        bundesland = ''
        if len(state_links) > 1:
            bundesland = state_links[-1].get_text(strip=True).strip('()')

        plz = ''
        city = ''
        location_match = re.match(r'(\d{5})\s+(.+)', location)
        if location_match:
            plz = location_match.group(1)
            city = location_match.group(2).strip()

        events.append({
            'name': name,
            'url': url,
            'plz': plz,
            'city': city,
            'bundesland': bundesland,
            'date_text': date_text,
        })

    return events


def scrape_detail(event_url):
    try:
        resp = session.get(event_url, timeout=10)
        if resp.status_code != 200:
            return None, None, None, None

        soup = BeautifulSoup(resp.text, 'html.parser')

        time_start = None
        time_end = None
        date_start = None
        date_end = None

        date_div = soup.select_one('.em-event-date')
        if date_div:
            date_text = date_div.get_text()
            date_match = re.findall(r'(\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4})', date_text)
            if date_match:
                date_start = parse_german_date(date_match[0])
                if len(date_match) > 1:
                    date_end = parse_german_date(date_match[1])

        time_div = soup.select_one('.em-event-time')
        if time_div:
            time_text = time_div.get_text()
            tm = re.findall(r'(\d{1,2}:\d{2})\s*[–\-]\s*(\d{1,2}:\d{2})', time_text)
            if tm:
                time_start = tm[0][0]
                time_end = tm[0][1]

        return date_start, date_end, time_start, time_end
    except Exception as e:
        print(f'  Error scraping detail {event_url}: {e}')
        return None, None, None, None


def run():
    print('Initializing database...')
    init_db()

    all_events = []
    page = 1
    while True:
        print(f'Scraping page {page}...')
        events = scrape_list_page(page)
        if not events:
            break
        all_events.extend(events)
        print(f'  Found {len(events)} events')
        page += 1
        if page > 50:
            break

    print(f'\nTotal events found: {len(all_events)}')

    for i, ev in enumerate(all_events):
        print(f'[{i+1}/{len(all_events)}] {ev["name"]} - {ev["city"]} ({ev["plz"]})')

        lat, lng = geocode(ev['plz'], ev['city'])
        if lat and lng:
            floh_id = save_flohmarkt(
                ev['name'], ev['plz'], ev['city'],
                ev['bundesland'], lat, lng, ev['url']
            )
            date_start, date_end, time_start, time_end = scrape_detail(ev['url'])
            save_termin(
                floh_id, str(date_start) if date_start else None,
                str(date_end) if date_end else None,
                time_start, time_end,
                ev['date_text'].split()[0] if ev['date_text'] else None,
                'once'
            )
        else:
            print(f'  Skipping (no coordinates)')

        time.sleep(0.5)

    print(f'\nDone! Scraped {len(all_events)} events.')


if __name__ == '__main__':
    run()
