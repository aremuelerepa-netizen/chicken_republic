from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import os, json, requests, random, threading, time

app = Flask(__name__)

# --- Enterprise Configuration ---
app.config.update(
    SESSION_PERMANENT=False,
    SESSION_TYPE="filesystem",
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "IBADAN_GOLDEN_KEY_2025")
)
Session(app)

# --- Credentials (Ensure these are set in your Environment Variables) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY")
MY_SITE_URL = "https://your-app-name.onrender.com"  # Update this after deployment
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- Nigerian Menu Database ---
def load_nigerian_menu():
    return {
        "Swallows": ["Amala and Abula", "Pounded Yam and Egusi", "Eba and Okro", "Tuwo Masara"],
        "Rice": ["Jollof Rice", "Fried Rice", "White Rice and Ayamase"],
        "Proteins": ["Crispy Chicken", "Grilled Fish", "Peppered Snail", "Assorted Meat"],
        "Sides": ["Dodo Cubes", "Moin Moin", "Salad", "Coleslaw"],
        "Prices": {"Standard Meal": 2500, "Combo Meal": 4500, "Side": 800}
    }

# --- Personality: The Ibadan Concierge ---
SYSTEM_PROMPT = """
You are Ahmad, the Lead Host at Chicken Republic Mokola. You are professional, witty, and a local expert on Ibadan.

CORE RULES:
1. LANGUAGE: Use clear, professional, and friendly English. No broken English.
2. IBADAN KNOWLEDGE: You know every corner of Ibadan (Bodija, Akobo, Challenge, Oluyole, UI, etc.). If a user mentions a location, engage with them about it.
3. CONVERSATION: You are a friend. Talk about life, weather, or jokes, but always bring it back to a good meal.
4. ORDERING PROCESS: When someone wants food:
   - Summarize the order clearly.
   - Mention their unique Order Number (CRM-XXXXX).
   - Tell them you are sending a Paystack link directly in the chat.
   - Ask if they want delivery to their Ibadan address or if they will pick it up at the Mokola kitchen.
5. FINAL STEP: Tell them to notify you once payment is made so you can confirm it on your dashboard.
"""

# --- Keep-Alive Heartbeat ---
def heartbeat():
    while True:
        try: requests.get(MY_SITE_URL, timeout=5)
        except: pass
        time.sleep(600)

threading.Thread(target=heartbeat, daemon=True).start()

# --- ROUTES ---

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "")
    menu = load_nigerian_menu()
    
    if 'history' not in session:
        session['history'] = []

    # --- Logic: Detect Order & Generate Paystack Link ---
    food_keywords = ["order", "buy", "pay", "jollof", "amala", "pounded", "chicken", "eba", "rice", "food"]
    payment_link = None
    order_id = f"CRM-{random.randint(10000, 99999)}"

    if any(word in user_msg.lower() for word in food_keywords):
        amount = 2500 # Base price for logic; can be expanded to parse specific prices
        
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
        payload = {
            "email": "customer@cr-mokola.com",
            "amount": amount * 100, # Kobo
            "reference": order_id,
            "callback_url": f"{MY_SITE_URL}/success",
            "metadata": {"cart": user_msg, "branch": "Mokola"}
        }
        
        try:
            r = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
            res_data = r.json()
            if res_data.get('status'):
                payment_link = res_data['data']['authorization_url']
        except Exception as e:
            print(f"Payment Error: {e}")

    # --- AI API Call ---
    context = f"MENU: {menu}. LOCATION: Mokola, Ibadan. USER ORDER ID: {order_id}"
    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n{context}"},
        *session['history'][-6:], 
        {"role": "user", "content": user_msg}
    ]

    try:
        response = requests.post(
            GROQ_BASE_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant", 
                "messages": messages, 
                "temperature": 0.75,
                "max_tokens": 250 
            },
            timeout=10
        )
        ai_reply = response.json()['choices'][0]['message']['content']
        
        # Save History
        session['history'].append({"role": "user", "content": user_msg})
        session['history'].append({"role": "assistant", "content": ai_reply})
        session.modified = True
        
        return jsonify({
            "reply": ai_reply,
            "payment_link": payment_link,
            "order_id": order_id
        })
    except Exception as e:
        return jsonify({"reply": "I'm sorry, I'm having a bit of trouble connecting to the kitchen. Can we try again?"})

@app.route("/success")
def success():
    # This page handles the redirect from Paystack
    ref = request.args.get('reference', 'CRM-PRO-ORDER')
    return render_template("success.html", order_id=ref)

if __name__ == "__main__":
    # Port 10000 is standard for Render deployments
    app.run(host="0.0.0.0", port=10000)
