# parse_wingo_sqlite.py
import json
import requests
import time
import os
import sqlite3
from datetime import datetime

# --- CONFIG ---
GAME_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M.json?"
HISTORY_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?"
DB_PATH = os.getenv("WINGO_DB", "wingo.db")

# --- DB UTILITIES ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rounds (
        round_id TEXT PRIMARY KEY,
        number INTEGER NOT NULL,
        color TEXT,
        category TEXT,
        timestamp INTEGER
    )
    """)
    # index on numeric ordering if needed
    cur.execute("CREATE INDEX IF NOT EXISTS idx_round_num ON rounds(round_id)")
    conn.commit()
    conn.close()

def round_exists(round_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM rounds WHERE round_id = ?", (round_id,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def insert_rounds(records):
    if not records:
        return 0
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = [(r["Round"], r["Number"], r["Color"], r["Category"], int(time.time())) for r in records]
    cur.executemany("INSERT OR IGNORE INTO rounds (round_id, number, color, category, timestamp) VALUES (?, ?, ?, ?, ?)", rows)
    conn.commit()
    added = conn.total_changes
    conn.close()
    return added

# --- PARSE LOGIC (same idea as your parse_wingo) ---
def fetch_and_parse():
    try:
        resp = requests.get(HISTORY_URL, timeout=12)
        resp.raise_for_status()
        data = resp.json().get("data", {}).get("list", [])
    except Exception as e:
        print("⚠️ fetch error:", e)
        return []

    parsed = []
    for item in data:
        issue_number = item.get("issueNumber")
        if not issue_number:
            continue
        if round_exists(issue_number):
            continue
        try:
            number = int(item.get("number", 0))
        except:
            continue
        color = item.get("color", "")
        category = "Small" if 0 <= number <= 4 else "Big"
        parsed.append({
            "Round": issue_number,
            "Number": number,
            "Color": color,
            "Category": category
        })
    # Sort ascending by round numeric (issueNumber appears numeric-ish)
    parsed.sort(key=lambda x: int(x["Round"]))
    return parsed

# --- MAIN LOOP ---
if __name__ == "__main__":
    init_db()
    print("✅ DB initialized:", DB_PATH)

    while True:
        # get timing info
        try:
            game_data = requests.get(GAME_URL, timeout=10).json()
            current_end = game_data["current"]["endTime"]
        except Exception as e:
            print("⚠️ error getting game info:", e)
            time.sleep(30)
            continue

        now_ms = int(time.time() * 1000)
        wait_time = (current_end - now_ms) / 1000.0
        if wait_time < 0:
            wait_time = 5
        print(f"\n⏳ next expected at {datetime.fromtimestamp(current_end/1000)} (wait {wait_time:.1f}s)")
        time.sleep(wait_time + 3)

        new_records = fetch_and_parse()
        if new_records:
            added = insert_rounds(new_records)
            print(f"💾 inserted ~{len(new_records)} records (db changes: {added})")
            for r in new_records:
                print(r["Round"], r["Number"], r["Category"], r["Color"])
        else:
            print("⚙️ no new rounds")
        time.sleep(5)
