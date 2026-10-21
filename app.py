# app.py
import json
import logging
import redis
from flask import Flask, request, make_response

app = Flask(__name__)
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

SESSION_TTL = 300  # 5 minutes


def ussd_response(body: str, status: int = 200):
    resp = make_response(body, status)
    resp.headers["Content-Type"] = "text/plain"
    return resp


def get_session(session_id):
    data = r.get(f"ussd:{session_id}")
    return json.loads(data) if data else {"step": "main"}


def save_session(session_id, state):
    r.setex(f"ussd:{session_id}", SESSION_TTL, json.dumps(state))


def handle_ussd(parts, phone_number, session_id):
    state = get_session(session_id)
    last_input = parts[-1] if parts else ""

    # Global command: 0 = go back to main menu
    if last_input == "0":
        state = {"step": "main"}
        save_session(session_id, state)
        return (
                "CON Welcome to Acme Wallet\n"
                "1. Check Balance\n"
                "2. Send Money\n"
                "3. Buy Airtime\n"
                "4. Exit"
            )

    step = state.get("step", "main")

    # ---- Main menu ----
    if step == "main":
        if last_input == "":
            return (
                "CON Welcome to Acme Wallet\n"
                "1. Check Balance\n"
                "2. Send Money\n"
                "3. Buy Airtime\n"
                "4. Exit"
            )
        if last_input == "1":
            return "END Your balance is KES 1,250.00"
        if last_input == "2":
            state["step"] = "recipient"
            save_session(session_id, state)
            return "CON Enter recipient phone number\n0. Back"
        if last_input == "3":
            state["step"] = "choice"
            save_session(session_id, state)
            return (
            f"CON Select an Option:\n"
            "1. Self\n"
            "2. Others"
            )
        if last_input == "4":
            return "END Goodbye!"
        return "END Invalid choice."

    # ---- Waiting for recipient ----
    if step == "recipient":
        if not last_input.isdigit() or len(last_input) < 9:
            return "END Invalid phone number. Please try again."
        state["recipient"] = last_input
        state["step"] = "amount"
        save_session(session_id, state)
        return "CON Enter amount (KES)\n0. Back"

    # ---- Waiting for amount ----
    if step == "amount":
        if not last_input.isdigit() or int(last_input) <= 0:
            return "END Invalid amount."
        state["amount"] = last_input
        state["step"] = "confirm"
        save_session(session_id, state)
        return (
            f"CON Send KES {state['amount']} to {state['recipient']}?\n"
            "1. Confirm\n"
            "2. Cancel"
        )


     # ---- Waiting for self amount ----
    if step == "self_amount":
        if not last_input.isdigit() or int(last_input) <= 0:
            return "END Invalid amount."
        state["self_amount"] = last_input
        state["step"] = "data_confirm"
        save_session(session_id, state)
        return (
            f"CON Send GHS {state['self_amount']} to {phone_number}?\n"
            "1. Confirm\n"
            "2. Cancel"
        )

    # ---- Waiting for confirmation ----
    if step == "confirm":
        if last_input == "1":
            recipient = state["recipient"]
            amount = state["amount"]
            # Real app: call payment API here
            save_session(session_id, {"step": "main"})
            return f"END Sent GHS {amount} to {recipient}. Thank you."
        save_session(session_id, {"step": "main"})
        return "END Transaction cancelled."

    # ---- Waiting for Self Data confirmation ----
    if step == "data_confirm":
        if last_input == "1":
            amount = state["self_amount"]
            # Real app: call payment API here
            save_session(session_id, {"step": "main"})
            return f"END Sent GHS {amount} to {phone_number}. Thank you."
        save_session(session_id, {"step": "main"})
        return "END Transaction cancelled."

    # ---- Waiting for Data Choice Self ----
    if step == "choice":
        if last_input == "1":
            if not last_input.isdigit() or int(last_input) <= 0 or int(last_input) > 2:
                return "END Invalid amount."
            state["choice"] = last_input
            state["step"] = "self_amount"
            save_session(session_id, state)
            return "CON Enter amount (GHS)\n"

    # ---- Waiting for Data Choice Others ----
    if step == "choice":
        if last_input == "2":
            state["step"] = "others_recipient"
            save_session(session_id, state)
            return "CON Enter recipient phone number\n0. Back"
            state["others_recipient"] = last_input
            state["step"] = "others_amount"
            save_session(session_id, state)
            return "CON Enter amount (KES)\n0. Back"
            



    # ---- Waiting for others amount ----
    if step == "others_amount":
        if not last_input.isdigit() or int(last_input) <= 0:
            return "END Invalid amount."
        state["amount"] = last_input
        state["step"] = "others_confirm"
        save_session(session_id, state)
        return (
            f"CON Send KES {state['others_amount']} to {state['others_recipient']}?\n"
            "1. Confirm\n"
            "2. Cancel"
        )

    # Fallback
    save_session(session_id, {"step": "main"})
    return "END Something went wrong. Returning to main menu."


@app.route("/ussd", methods=["POST"])
def ussd():
    try:
        session_id = request.values.get("sessionId", "")
        phone_number = request.values.get("phoneNumber", "")
        text = request.values.get("text", "").strip()

        parts = text.split("*") if text else []
        response = handle_ussd(parts, phone_number, session_id)

        log.info(f"session={session_id} text={text!r} -> {response[:40]!r}")
        return ussd_response(response)

    except Exception:
        log.exception("USSD handler crashed")
        return ussd_response("END Sorry, something went wrong.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)