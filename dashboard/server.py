from flask import Flask, jsonify, request, send_file
import json, random, subprocess, os

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(DASHBOARD_DIR, ".."))
SHADYSIDE = os.path.join(PROJECT_ROOT, "Shadyside.json")
STOPS = os.path.join(PROJECT_ROOT, "stops.json")

app = Flask(__name__)

write_json(STOPS, {})


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


@app.route("/")
def index():
    return send_file(os.path.join(DASHBOARD_DIR, "index.html"))


@app.route("/api/all-stops")
def all_stops():
    return jsonify(read_json(SHADYSIDE))


@app.route("/api/stops")
def get_stops():
    return jsonify(read_json(STOPS))


@app.route("/api/simulate-tap", methods=["POST"])
def simulate_tap():
    all_s = read_json(SHADYSIDE)
    current = read_json(STOPS)
    available = {k: v for k, v in all_s.items() if k not in current}
    if not available:
        return jsonify({"error": "All stops already added"}), 400
    code = random.choice(list(available.keys()))
    current[code] = available[code]
    write_json(STOPS, current)
    return jsonify({"added": code, "stops": current})


@app.route("/api/clear-last", methods=["POST"])
def clear_last():
    current = read_json(STOPS)
    if not current:
        return jsonify({"error": "No stops to clear"}), 400
    items = list(current.items())
    removed_code = items[-1][0]
    items.pop()
    write_json(STOPS, dict(items))
    return jsonify({"removed": removed_code, "stops": dict(items)})


@app.route("/api/add-stop", methods=["POST"])
def add_stop():
    code = request.json.get("code")
    all_s = read_json(SHADYSIDE)
    if code not in all_s:
        return jsonify({"error": "Invalid stop code"}), 400
    current = read_json(STOPS)
    if code in current:
        return jsonify({"error": "Stop already added"}), 400
    current[code] = all_s[code]
    write_json(STOPS, current)
    return jsonify({"added": code, "stops": current})


@app.route("/api/plan-route", methods=["POST"])
def plan_route():
    current = read_json(STOPS)
    if len(current) < 1:
        return jsonify({"error": "Add at least one stop first"}), 400
    try:
        result = subprocess.run(
            ["python3", "route_planner.py"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Route planning timed out"}), 500
    if result.returncode != 0:
        return jsonify({"error": result.stderr.strip() or "Route planning failed"}), 500
    url = ""
    for line in reversed(result.stdout.strip().split("\n")):
        if line.startswith("http"):
            url = line.strip()
            break
    if not url:
        return jsonify({"error": "No route URL in output"}), 500
    return jsonify({"url": url})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
