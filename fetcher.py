import json
import requests
import time
import sqlite3
import os
from datetime import datetime

# --- CONFIG --- #
GAME_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M.json?"
HISTORY_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json?"
DB_FILE = "wingo.db"

# --- DATABASE SETUP --- #
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

print("✅ Database initialized and table 'rounds' ready.\n")

# --- FETCH HISTORY DATA --- #
def fetch_history():
    try:
        resp = requests.get(HISTORY_URL, timeout=10)
        data = resp.json()["data"]["list"]
    except Exception as e:
        print(f"⚠️ Error fetching history: {e}")
        return []

    results = []
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    for item in data:
        issue = item["issueNumber"]
        number = int(item["number"])
        color = item["color"]
        category = "Small" if number <= 4 else "Big"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            c.execute("""
                INSERT OR IGNORE INTO rounds (issue_number, number, color, category, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (issue, number, color, category, ts))
            if c.rowcount > 0:
                results.append({
                    "issue": issue,
                    "number": number,
                    "color": color,
                    "category": category
                })
        except Exception as e:
            print(f"⚠️ DB insert error: {e}")
            continue

    conn.commit()
    conn.close()
    return results

# --- PRETTY PRINT FUNCTION --- #
def print_results(records):
    if not records:
        return
    print("\n🧾 New Rounds Added:")
    print(f"{'Round':<20} {'Number':<8} {'Color':<18} {'Category':<10}")
    print("-" * 60)
    for r in records:
        color_display = r['color']
        if "red" in color_display: color_display = color_display.replace("red", "🔴 red")
        if "green" in color_display: color_display = color_display.replace("green", "🟢 green")
        if "violet" in color_display: color_display = color_display.replace("violet", "🟣 violet")
        print(f"{r['issue']:<20} {r['number']:<8} {color_display:<18} {r['category']:<10}")
    print("-" * 60)

# --- MAIN LOOP --- #
while True:
    # Get next round info (with ts to force refresh)
    ts = int(time.time() * 1000)
    try:
        game_data = requests.get(f"{GAME_URL}ts={ts}", timeout=10).json()
        current_end = game_data["current"]["endTime"]
    except Exception as e:
        print(f"⚠️ Error fetching live round info: {e}")
        time.sleep(10)
        continue

    # Calculate wait time until next round
    now_ms = int(time.time() * 1000)
    wait_time = (current_end - now_ms) / 1000
    if wait_time < 0:
        wait_time = 5

    print(f"\n⏳ Next round expected at {time.ctime(current_end / 1000)} "
          f"({wait_time:.1f}s from now)")
    time.sleep(wait_time + 3)  # buffer after round ends

    # Fetch and save rounds
    new_data = fetch_history()
    if new_data:
        print_results(new_data)
    else:
        print("⚙️ No new rounds found (data unchanged).")

    print("🔁 Waiting for next update...\n")
    time.sleep(5)
