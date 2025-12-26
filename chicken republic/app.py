from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import json
import requests
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

app = Flask(__name__)
BOT_NAME = "Chicken Republic Bot"

# Paystackimport os
LLAMA_API_KEY = os.environ.get("LLAMA_API_KEY")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY")
LLAMA_API_URL = os.environ.get("LLAMA_API_URL")
# Load branch data
with open("branch_data.json") as f:
    branch_db = json.load(f)

def create_payment_link(amount, email="demo@example.com", item=""):
    url = "https://paystack.shop/pay/chickenrepublic"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    data = {
        "email": email,
        "amount": amount * 100,
        "metadata": {"item": item}
    }
    r = requests.post(url, json=data, headers=headers)
    res = r.json()
    if res['status']:
        return res['data']['authorization_url']
    return None

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.form.get("Body").lower()
    resp = MessagingResponse()

    # Optional: detect branch keyword
    branch_name = "Mokola"
    for b in branch_db["branches"]:
        if b.lower() in incoming_msg:
            branch_name = b
            break
    branch = branch_db["branches"][branch_name]

    # Show menu
    if "menu" in incoming_msg:
        items = [f"{i['item']} - ₦{i['price']}" for i in branch['menu']]
        reply_text = f"{BOT_NAME}: {branch['name']} Menu:\n" + "\n".join(items)

    # Show promotions
    elif "promotion" in incoming_msg or "offer" in incoming_msg:
        promos = [f"{p['name']} (valid until {p['valid_until']})" for p in branch['promotions']]
        reply_text = f"{BOT_NAME}: Current promotions at {branch['name']}:\n" + "\n".join(promos)

    # Place order
    elif "order" in incoming_msg:
        item_name = incoming_msg.replace("order", "").strip()
        item = next((i for i in branch['menu'] if i['item'].lower() == item_name.lower()), None)
        if item:
            payment_link = create_payment_link(item['price'], item=item_name)
            branch['orders'].append({"item": item_name, "paid": False})
            reply_text = f"{BOT_NAME}: You ordered {item_name} (₦{item['price']}). Pay here to confirm:\n{payment_link}"
        else:
            reply_text = f"{BOT_NAME}: Sorry, {item_name} is not on the menu at {branch['name']}."

    # General questions handled by LLaMA
    else:
        payload = {"prompt": f"You are a helpful assistant for {branch['name']}. Answer: {incoming_msg}"}
        llama_resp = requests.post(LLAMA_API_URL, headers={"Authorization": f"Bearer {LLAMA_API_KEY}"}, json=payload)
        data = llama_resp.json()
        reply_text = data.get("response", f"{BOT_NAME}: Sorry, I couldn't understand that.")

    resp.message(reply_text)
    return str(resp)

# Payment webhook
@app.route("/payment_webhook", methods=["POST"])
def payment_webhook():
    payload = request.json
    if payload.get('event') == 'charge.success':
        item_name = payload['data']['metadata']['item']
        # Mark order as paid
        for b in branch_db["branches"]:
            for order in branch_db["branches"][b]["orders"]:
                if order['item'].lower() == item_name.lower():
                    order['paid'] = True
        print(f"Payment confirmed for {item_name}")
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)
