from flask import Flask, render_template, jsonify, request
import sqlite3

app = Flask(__name__)

DB_FILE = "wingo.db"

# Fetch all rounds for chart
def get_all_rounds():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT issue_number, number FROM rounds ORDER BY issue_number ASC")
    data = c.fetchall()
    conn.close()
    rounds = [{"issue": r[0], "number": r[1]} for r in data]
    return rounds

# Homepage
@app.route('/')
def index():
    return render_template('dashboard.html')

# API: all data for chart
@app.route('/api/rounds')
def api_rounds():
    return jsonify(get_all_rounds())

# API: search sequence
@app.route('/api/search')
def search_sequence():
    seq = request.args.get("seq", "")
    if not seq:
        return jsonify({"error": "No sequence provided"})
    
    seq_nums = [int(x) for x in seq.split(",") if x.strip().isdigit()]
    rounds = get_all_rounds()
    matches = []

    for i in range(len(rounds) - len(seq_nums)):
        window = [r["number"] for r in rounds[i:i + len(seq_nums)]]
        if window == seq_nums:
            matches.append(rounds[i:i + len(seq_nums) + 5])  # 5 rounds after match
    
    return jsonify({"matches": matches, "count": len(matches)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
