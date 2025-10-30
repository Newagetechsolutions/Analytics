from flask import Flask, render_template, jsonify, request
import sqlite3
from fetcher import start_background_fetcher
import os

app = Flask(__name__)

DB_FILE = "wingo.db"

# =========================================================
# Helper: Database access
# =========================================================
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# Flask Routes
# =========================================================

@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/rounds")
def get_rounds():
    """Return latest N rounds for visualization."""
    limit = int(request.args.get("limit", 500))
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT issue_number, number, category, timestamp FROM rounds ORDER BY timestamp ASC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()

    data = [dict(r) for r in rows]
    return jsonify(data)


@app.route("/api/search_sequence")
def search_sequence():
    """Find all occurrences of a number sequence."""
    seq_str = request.args.get("seq", "")
    seq = [int(x) for x in seq_str.split(",") if x.strip().isdigit()]
    if not seq:
        return jsonify({"error": "No valid sequence provided."}), 400

    conn = get_db_connection()
    numbers = [r["number"] for r in conn.execute("SELECT number FROM rounds ORDER BY timestamp ASC").fetchall()]
    conn.close()

    matches = []
    L = len(seq)
    for i in range(len(numbers) - L + 1):
        if numbers[i:i+L] == seq:
            matches.append({"index": i, "sequence": seq})

    return jsonify({"sequence": seq, "matches": matches, "count": len(matches)})


# =========================================================
# Start background data fetcher
# =========================================================

if not os.environ.get("FETCHER_RUNNING"):
    os.environ["FETCHER_RUNNING"] = "1"
    start_background_fetcher()
    print("[App] Background fetcher started.")

# =========================================================
# Run Flask (for manual testing)
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
