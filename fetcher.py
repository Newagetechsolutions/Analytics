import requests
import sqlite3
import time
from datetime import datetime
import threading

# ===============================
# CONFIGURATION
# ===============================
HISTORY_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?"
NEXT_ROUND_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/WinGo_1M.json"
DB_FILE = "wingo.db"

# ===============================
# DATABASE SETUP
# ===============================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS rounds (
            issue_number TEXT PRIMARY KEY,
            number INTEGER,
            color TEXT,
            category TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

# ===============================
# FETCH AND CLASSIFY
# ===============================

def get_next_round_time():
    """Fetch next round end time from API."""
    try:
        resp = requests.get(NEXT_ROUND_URL, timeout=10)
        data = resp.json()
        end_time = data.get("data", {}).get("current", {}).get("endTime")
        if not end_time:
            return None
        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        return end_dt
    except Exception as e:
        print("Error fetching next round time:", e)
        return None


def fetch_latest_rounds():
    """Fetch the latest round data from the history API."""
    try:
        resp = requests.get(HISTORY_URL, timeout=10)
        data = resp.json()
        rounds = data.get("data", {}).get("list", [])
        return rounds
    except Exception as e:
        print("Error fetching history:", e)
        return []


def store_new_rounds():
    """Fetch new rounds and store only unseen ones."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    rounds = fetch_latest_rounds()
    if not rounds:
        print("[Fetcher] No data received.")
        return

    new_count = 0
    for r in rounds:
        issue_number = r.get("issueNumber")
        number = int(r.get("number", -1))
        color = r.get("color", "")
        category = "Small" if 0 <= number <= 4 else "Big"

        # insert only if new
        try:
            c.execute("""
                INSERT INTO rounds (issue_number, number, color, category, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (issue_number, number, color, category, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            new_count += 1
        except sqlite3.IntegrityError:
            pass  # already exists

    conn.close()
    if new_count:
        print(f"[Fetcher] Added {new_count} new rounds.")
    else:
        print("[Fetcher] No new rounds found.")


def fetch_loop():
    """Continuously fetch new round data based on next round timing."""
    init_db()
    print("[Fetcher] Started WinGo background collector.")

    while True:
        next_time = get_next_round_time()
        if not next_time:
            print("[Fetcher] Could not get next round time, retrying in 60s.")
            time.sleep(60)
            continue

        now = datetime.now()
        wait_seconds = (next_time - now).total_seconds() + 3  # fetch 3s after round end
        if wait_seconds < 0:
            wait_seconds = 10

        print(f"[Fetcher] Waiting {round(wait_seconds)}s until next fetch ({next_time}).")
        time.sleep(wait_seconds)

        store_new_rounds()


def start_background_fetcher():
    """Run fetch_loop in a daemon thread."""
    t = threading.Thread(target=fetch_loop, daemon=True)
    t.start()
    print("[Fetcher] Background thread started.")
