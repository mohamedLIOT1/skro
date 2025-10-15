import os
import json
import threading
from flask import Flask, request, jsonify

# --- REST API لربط النقاط مع الداشبورد ---
API_SECRET = os.getenv("SCRU_API_SECRET", "change_this_secret")  # ضع نفس القيمة في الداشبورد

app = Flask("scru_api")

@app.route("/api/guild/<guild_id>/points", methods=["GET"])
def get_guild_points(guild_id):
    # تحقق التوكن البسيط
    token = request.headers.get("Authorization", "")
    if token != f"Bearer {API_SECRET}":
        return jsonify({"error": "unauthorized"}), 401
    # جلب النقاط من points_manager
    data = points_manager.data.get(str(guild_id), {})
    return jsonify(data)

@app.route("/api/guild/<guild_id>/points/<user_id>", methods=["GET"])
def get_user_points(guild_id, user_id):
    token = request.headers.get("Authorization", "")
    if token != f"Bearer {API_SECRET}":
        return jsonify({"error": "unauthorized"}), 401
    stats = points_manager.data.get(str(guild_id), {}).get(str(user_id), {})
    return jsonify(stats)

# يمكنك إضافة PUT/POST لتعديل النقاط إذا أردت لاحقاً

def run_api():
    app.run(host="0.0.0.0", port=5050)

# شغّل Flask في ثريد منفصل حتى لا يعطل البوت
threading.Thread(target=run_api, daemon=True).start()