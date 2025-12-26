from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import os, json, requests, random, threading, time

app = Flask(__name__)

# --- Configuration ---
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = "CR_Mokola_Secret_Key_2025"
Session(app)

# --- API Keys (Set these on Render!) ---
LLAMA_API_KEY = os.environ.get("GROQ_API_KEY")
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY")
LLAMA_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- Feature 1: The Heartbeat (Keep Render Awake) ---
def keep_alive():
    """Pings the app every 10 minutes to prevent Render from sleeping."""
    # Replace with your actual Render URL once deployed
    app_url = "https://your-app-name.onrender.com" 
    while True:
        try:
            requests.get(app_url)
            print("Heartbeat sent: Keeping the Digital Branch active!")
        except:
            print("Heartbeat failed. Waiting for next cycle.")
        time.sleep(600) # 10 minutes

# Start the heartbeat thread automatically
threading.Thread(target=keep_alive, daemon=True).start()

SYSTEM_PROMPT = """
You are the friendly, energetic AI host for Chicken Republic Mokola.
Personality: Warm, helpful, and use light Nigerian slang (e.g., 'How body?', 'Enjoy your meal o!').
Rules:
1. Always be polite and answer any question.
2. Use the provided Menu for prices.
3. If they want to order, tell them to use the 'Checkout' button on the dashboard.
4. Suggest 'Dodo Cubes' as a side!
"""
@app.route("/success")
def success():
    # We get the order ID from the URL after payment
    order_id = request.args.get('reference', 'CRM-0000')
    return render_template("success.html", order_id=order_id)
    
def get_branch_data():
    try:
        with open("branch_data.json", "r") as f:
            return json.load(f)["branches"]["mokola"]
    except: return {"name": "Chicken Republic", "menu": []}

# --- ROUTES ---

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    branch = get_branch_data()
    
    if 'history' not in session:
        session['history'] = []

    context = f"Branch Info: {branch['name']} in Ibadan. Menu: {branch['menu']}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n" + context}]
    messages.extend(session['history'][-6:]) 
    messages.append({"role": "user", "content": user_input})

    try:
        r = requests.post(LLAMA_API_URL, 
            headers={"Authorization": f"Bearer {LLAMA_API_KEY}"},
            json={"model": "llama-3.1-8b-instant", "messages": messages, "temperature": 0.8},
            timeout=10
        )
        ai_reply = r.json()['choices'][0]['message']['content']
        
        session['history'].append({"role": "user", "content": user_input})
        session['history'].append({"role": "assistant", "content": ai_reply})
        session.modified = True
        
        return jsonify({"reply": ai_reply})
    except:
        return jsonify({"reply": "Oya, my network reach small glitch. Try again for me?"})

# --- Feature 2: Real Payment Initialization ---
@app.route("/initialize_payment", methods=["POST"])
def initialize_payment():
    data = request.json
    order_id = f"CRM-{random.randint(1000, 9999)}" # Unique Order Number
    
    paystack_data = {
        "email": "customer@mokola-express.com",
        "amount": int(data['amount']) * 100, # Paystack uses Kobo
        "reference": order_id,
        "callback_url": "https://your-app-name.onrender.com/success",
        "metadata": {
            "location": data.get("location"),
            "cart": data.get("cart")
        }
    }
    
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
    try:
        r = requests.post("https://api.paystack.co/transaction/initialize", 
                          json=paystack_data, headers=headers)
        return jsonify(r.json())
    except:
        return jsonify({"status": False, "message": "Payment system offline"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

