# app.py
from flask import Flask, jsonify, request, render_template, g
import sqlite3
import os

DB_PATH = os.getenv("WINGO_DB", "wingo.db")

app = Flask(__name__, static_folder="static", template_folder="templates")

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(error):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Serve dashboard page
@app.route("/")
def index():
    return render_template("dashboard.html")

# API: get all rounds (with optional limit/offset or range)
@app.route("/api/rounds")
def api_rounds():
    limit = int(request.args.get("limit", 1000))
    offset = int(request.args.get("offset", 0))
    db = get_db()
    cur = db.execute("SELECT round_id, number, color, category FROM rounds ORDER BY CAST(round_id AS INTEGER) ASC LIMIT ? OFFSET ?", (limit, offset))
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)

# API: rounds between two round_ids (inclusive)
@app.route("/api/rounds/range")
def api_rounds_range():
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        return jsonify({"error":"start and end required"}), 400
    db = get_db()
    cur = db.execute("SELECT round_id, number, color, category FROM rounds WHERE CAST(round_id AS INTEGER) BETWEEN ? AND ? ORDER BY CAST(round_id AS INTEGER) ASC", (start, end))
    return jsonify([dict(r) for r in cur.fetchall()])

# API: sequence search
# Query parameters:
#   seq = comma separated sequence e.g. 5,4,3,1
#   type = "number" (default) or "category" (for Big/Small)
# returns matches: list of {start_round, indexes, following: [nextNnumbers...]}
@app.route("/api/search_sequence")
def api_search_sequence():
    seq_raw = request.args.get("seq", "")
    search_type = request.args.get("type", "number")  # number or category
    after = int(request.args.get("after", 5))  # how many following items to return
    if not seq_raw:
        return jsonify({"error":"seq param required"}), 400

    seq_list = [s.strip() for s in seq_raw.split(",") if s.strip() != ""]
    if not seq_list:
        return jsonify([])

    db = get_db()
    # fetch all rounds in order
    cur = db.execute("SELECT round_id, number, category FROM rounds ORDER BY CAST(round_id AS INTEGER) ASC")
    rows = cur.fetchall()
    values = []
    ids = []
    for r in rows:
        ids.append(r["round_id"])
        if search_type == "category":
            values.append(r["category"])
        else:
            values.append(str(r["number"]))

    results = []
    L = len(values)
    seq_len = len(seq_list)
    for i in range(L - seq_len + 1):
        window = values[i:i+seq_len]
        if window == seq_list:
            # collect following numbers after the sequence
            following = []
            for j in range(i+seq_len, min(i+seq_len+after, L)):
                following.append({"round_id": ids[j], "number": int(values[j]) if search_type!="category" else values[j]})
            results.append({
                "start_index": i,
                "start_round": ids[i],
                "matched_sequence": window,
                "following": following
            })
    return jsonify(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
