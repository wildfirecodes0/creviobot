import logging
from flask import Blueprint, request, jsonify

import config
import db
from utils import is_valid_india_number
from services import edesy

log = logging.getLogger("crevio.public_api")

public_api_bp = Blueprint("public_api", __name__)


def _authenticate():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip() if auth.startswith("Bearer ") else auth.strip()
    if not token:
        return None
    return db.get_user_by_api_key(token)


@public_api_bp.route("/api/v1/call", methods=["POST"])
def api_make_call():
    user = _authenticate()
    if not user:
        return jsonify({"error": "Invalid or missing API key."}), 401

    balance = float(user["balance"])
    if balance < config.API_MIN_BALANCE:
        return jsonify({"error": f"Insufficient balance. Minimum {config.API_MIN_BALANCE} {config.BOT_CURRENCY} required."}), 402

    if not user.get("phone_number"):
        return jsonify({"error": "No phone number on file. Share your contact with the bot at least once first."}), 400

    if user.get("active_call_id"):
        return jsonify({"error": "You already have an active call."}), 409

    body = request.get_json(silent=True) or {}
    number = str(body.get("number", "")).strip()
    if not is_valid_india_number(number):
        return jsonify({"error": "Invalid number. Use +91XXXXXXXXXX format, India only."}), 400

    min_needed = config.MIN_CALL_START_BALANCE_MIN * config.CALL_RATE_PER_MIN
    if balance < min_needed:
        return jsonify({"error": f"Insufficient balance for even {config.MIN_CALL_START_BALANCE_MIN} minute(s)."}), 402

    call_id = db.create_call(user["telegram_id"], number, via_api=True)
    db.set_active_call(user["telegram_id"], call_id)

    try:
        result = edesy.initiate_masked_call(user["phone_number"], number)
        edesy_call_id = result.get("call_id") or result.get("id")
        db.set_call_edesy_id(call_id, edesy_call_id)
    except Exception as e:
        log.error("API call initiation failed: %s", e)
        db.end_call(call_id, "failed", 0, 0)
        db.set_active_call(user["telegram_id"], None)
        return jsonify({"error": "Call could not be initiated with the provider."}), 502

    return jsonify({"call_id": call_id, "status": "initiated"}), 201


@public_api_bp.route("/api/v1/call/<int:call_id>", methods=["GET"])
def api_call_status(call_id):
    user = _authenticate()
    if not user:
        return jsonify({"error": "Invalid or missing API key."}), 401

    call = db.get_call(call_id)
    if not call or call["telegram_id"] != user["telegram_id"]:
        return jsonify({"error": "Call not found."}), 404

    return jsonify({
        "call_id": call["id"],
        "status": call["status"],
        "duration_seconds": call["duration_sec"],
        "cost": call["cost"],
    })
