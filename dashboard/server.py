from flask import Flask, jsonify, request, send_file
import json, random, subprocess, os
from openai import OpenAI

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(DASHBOARD_DIR, ".."))
SHADYSIDE = os.path.join(PROJECT_ROOT, "Shadyside.json")
STOPS = os.path.join(PROJECT_ROOT, "stops.json")

app = Flask(__name__)

xai = OpenAI(
    api_key=os.environ.get("XAI_API_KEY", ""),
    base_url="https://api.x.ai/v1",
)

VOICE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "clear_last",
            "description": "Remove the most recently added stop from the route.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_stop",
            "description": "Add a stop by its code (intersection name like 'Centre+Aiken').",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Stop code, e.g. 'Centre+Aiken', 'Fifth+S.Negley'",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_route",
            "description": "Plan an optimized route through all current stops and open Google Maps.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _build_system_prompt():
    all_stops = read_json(SHADYSIDE)
    codes = ", ".join(all_stops.keys())
    current = read_json(STOPS)
    current_list = ", ".join(current.keys()) if current else "(none)"
    return (
        "You are a voice assistant for a CMU Escort bus driver. "
        "The driver speaks commands to manage tonight's route stops.\n\n"
        f"Valid stop codes: {codes}\n\n"
        f"Currently added stops: {current_list}\n\n"
        "When the driver names an intersection, match it to the closest valid stop code. "
        "For example 'Center and Aiken' means 'Centre+Annie' is wrong — look for the best match. "
        "'Fifth and Negley' means 'Fifth+S.Negley'. 'Walgreens' means 'Centre+Walgreens'. "
        "Use the tools to carry out the driver's request. You may call multiple tools in sequence. "
        "After executing, reply with a brief one-sentence confirmation of what you did."
    )


def _exec_tool(name, args):
    if name == "clear_last":
        current = read_json(STOPS)
        if not current:
            return {"error": "No stops to clear"}
        items = list(current.items())
        removed = items[-1][0]
        items.pop()
        write_json(STOPS, dict(items))
        return {"removed": removed, "stops": dict(items)}
    elif name == "add_stop":
        code = args.get("code", "")
        all_s = read_json(SHADYSIDE)
        if code not in all_s:
            return {"error": f"Invalid stop code: {code}"}
        current = read_json(STOPS)
        if code in current:
            return {"error": "Stop already added"}
        current[code] = all_s[code]
        write_json(STOPS, current)
        return {"added": code, "stops": current}
    elif name == "plan_route":
        current = read_json(STOPS)
        if len(current) < 1:
            return {"error": "Add at least one stop first"}
        try:
            result = subprocess.run(
                ["python3", "route_planner.py"],
                cwd=PROJECT_ROOT,
                capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            return {"error": "Route planning timed out"}
        if result.returncode != 0:
            return {"error": result.stderr.strip() or "Route planning failed"}
        url = ""
        for line in reversed(result.stdout.strip().split("\n")):
            if line.startswith("http"):
                url = line.strip()
                break
        if not url:
            return {"error": "No route URL in output"}
        return {"url": url}
    return {"error": "Unknown tool"}


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


write_json(STOPS, {})


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


@app.route("/api/voice-command", methods=["POST"])
def voice_command():
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    messages = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": text},
    ]

    route_url = None
    for _ in range(5):
        resp = xai.chat.completions.create(
            model="grok-3-mini",
            messages=messages,
            tools=VOICE_TOOLS,
            tool_choice="auto",
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            break

        messages.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            result = _exec_tool(tc.function.name, args)
            if "url" in result:
                route_url = result["url"]
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

    reply = msg.content or "Done."
    stops = read_json(STOPS)
    out = {"reply": reply, "stops": stops}
    if route_url:
        out["url"] = route_url
    return jsonify(out)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
