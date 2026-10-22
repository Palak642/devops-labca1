import math

from flask import Flask, jsonify, request


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.get("/api/greet/<name>")
    def greet(name: str):
        cleaned_name = name.strip()
        if not cleaned_name or len(cleaned_name) > 80 or any(
            ord(character) < 32 for character in cleaned_name
        ):
            return jsonify(error="name must be 1-80 printable characters"), 400
        return jsonify(message=f"Hello, {cleaned_name}!"), 200

    @app.post("/api/add")
    def add_numbers():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="a JSON object is required"), 400

        left = payload.get("left")
        right = payload.get("right")
        if type(left) not in (int, float) or type(right) not in (int, float):
            return jsonify(error="left and right must be numbers"), 400
        if any(
            isinstance(number, float) and not math.isfinite(number)
            for number in (left, right)
        ):
            return jsonify(error="numbers must be finite"), 400

        return jsonify(result=left + right), 200

    return app
