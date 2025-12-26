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

# --- API Configuration ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY")

# This is YOUR website URL (Required for Paystack to redirect to your success page)
MY_SITE_URL = "https://chicken-republic-r4bk.onrender.com" 

# This is the GROQ API URL
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- Feature 1: The Heartbeat (Keep Render Awake) ---
def heartbeat():
    while True:
        try:
            requests.get(MY_SITE_URL, timeout=5)
        except:
            pass
        time.sleep(600)

threading.Thread(target=heartbeat, daemon=True).start()

# --- Content Loader ---
def load_mokola_assets():
    try:
        with open("branch_data.json", "r") as f:
            return json.load(f)["branches"]["mokola"]
    except:
        return {"menu": "Refuel Meal: 2500, Citizens Meal: 3800, Dodo Cubes: 800"}

# --- AI Personality (Snappy & Human) ---
SYSTEM_PROMPT = """
You are 'Ayo', the friendly host at Chicken Republic Mokola. 
RULES:
1. Short replies ONLY (Max 2 sentences).
2. Use slang like 'How body?', 'Oya', 'Abeg'.
3. Don't be a robot. Chat about anything, but keep it light and foodie.
4. If food is mentioned, suggest Refuel Meal + Dodo Cubes.
"""

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

    context = f"MENU: {branch_info['menu']}. Location: Mokola, Ibadan."
    
    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n{context}"},
        *session['history'][-4:], 
        {"role": "user", "content": user_msg}
    ]

    try:
        response = requests.post(
            GROQ_BASE_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant", 
                "messages": messages, 
                "temperature": 0.7,
                "max_tokens": 80 
            },
            timeout=10
        )
        ai_reply = response.json()['choices'][0]['message']['content']
        
        session['history'].append({"role": "user", "content": user_msg})
        session['history'].append({"role": "assistant", "content": ai_reply})
        session.modified = True
        
        return jsonify({"reply": ai_reply})
    except:
        return jsonify({"reply": "Network glitch, abeg try again! 🍗"})

@app.route("/initialize_payment", methods=["POST"])
def initialize_payment():
    order_data = request.json
    order_ref = f"CR-MOK-{random.randint(10000, 99999)}"
    
    payload = {
        "email": "customer@cr-mokola.com",
        "amount": int(order_data['amount']) * 100,
        "reference": order_ref,
        "callback_url": f"{MY_SITE_URL}/success", # Returns customer to your site
        "metadata": {"location": order_data.get("location"), "cart": order_data.get("cart")}
    }
    
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
    try:
        res = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
        return jsonify(res.json())
    except:
        return jsonify({"status": False, "message": "Kitchen server busy."}), 500

@app.route("/success")
def success():
    ref = request.args.get('reference', 'CRM-ORDER')
    return render_template("success.html", order_id=ref)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
