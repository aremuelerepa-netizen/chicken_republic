from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import os, json, requests, random, threading, time

app = Flask(__name__)

# --- Enterprise Config ---
app.config.update(
    SESSION_PERMANENT=False,
    SESSION_TYPE="filesystem",
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "CR_Mokola_Express_2025")
)
Session(app)

# Credentials
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY")
BASE_URL = "https://your-app-name.onrender.com" # Change this after deployment

# --- Background: The Keep-Alive Heartbeat ---
def heartbeat():
    while True:
        try:
            requests.get(BASE_URL, timeout=5)
            print("💓 System Status: Mokola Branch is Awake & Active.")
        except Exception as e:
            print(f"💔 Heartbeat skipped: {e}")
        time.sleep(600)

threading.Thread(target=heartbeat, daemon=True).start()

# --- Content Loader ---
def load_mokola_assets():
    try:
        with open("branch_data.json", "r") as f:
            data = json.load(f)
            return data["branches"]["mokola"]
    except Exception:
        return {"menu": "Refuel Meal: 2500, Citizens Meal: 3800, Dodo Cubes: 800"}

# --- AI Sales Personality ---
SYSTEM_PROMPT = """
You are 'Ayo', the Lead Digital Host at Chicken Republic Mokola, Ibadan. 
Your goal: Turn inquiries into orders.

TONE: Professional but 'Naija-friendly'. Use phrases like 'Welcome to the Republic!', 'Enjoy your meal o!', 'How body?'.

SALES STRATEGY:
1. If they ask for chicken, suggest a 'Refuel Meal'. 
2. ALWAYS recommend 'Dodo Cubes' or 'Coleslaw' as a side.
3. If they mention delivery, tell them to 'Lock GPS' on the dashboard.
4. Keep answers short. Format prices clearly in Naira (₦).
"""

# --- ROUTES ---

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "")
    branch_info = load_mokola_assets()
    
    if 'history' not in session:
        session['history'] = []

    # Build High-Context Prompt
    context = f"CURRENT MENU & PRICES: {branch_info['menu']}. LOCATION: Mokola Roundabout, Ibadan."
    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n{context}"},
        *session['history'][-6:], # Last 3 full exchanges
        {"role": "user", "content": user_msg}
    ]

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model": "llama-3.1-8b-instant", "messages": messages, "temperature": 0.6},
            timeout=10
        )
        ai_reply = response.json()['choices'][0]['message']['content']
        
        # Update Memory
        session['history'].append({"role": "user", "content": user_msg})
        session['history'].append({"role": "assistant", "content": ai_reply})
        session.modified = True
        
        return jsonify({"reply": ai_reply})
    except Exception as e:
        return jsonify({"reply": "My network reach small glitch, abeg try again!"}), 500

@app.route("/initialize_payment", methods=["POST"])
def initialize_payment():
    order_data = request.json
    order_ref = f"CR-MOK-{random.randint(10000, 99999)}"
    
    # Paystack payload optimized for staff tracking
    payload = {
        "email": "orders@chicken-republic.com", # Corporate routing email
        "amount": int(order_data['amount']) * 100,
        "reference": order_ref,
        "callback_url": f"{BASE_URL}/success",
        "metadata": {
            "custom_fields": [
                {"display_name": "Delivery Point", "variable_name": "location", "value": order_data.get("location")},
                {"display_name": "Items", "variable_name": "cart", "value": order_data.get("cart")}
            ]
        }
    }
    
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
    try:
        res = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
        return jsonify(res.json())
    except:
        return jsonify({"status": False, "message": "Kitchen server busy."}), 500

@app.route("/success")
def success():
    ref = request.args.get('reference')
    return render_template("success.html", order_id=ref)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
