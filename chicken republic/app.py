from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import os, json, requests, random, threading, time

app = Flask(__name__)

# --- Enterprise Config ---
app.config.update(
    SESSION_PERMANENT=False,
    SESSION_TYPE="filesystem",
    SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "IBADAN_PRO_2025")
)
Session(app)

# Credentials
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY")
MY_SITE_URL = "https://your-app-name.onrender.com" 
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- Ibadan & Food Data Logic ---
def load_nigerian_menu():
    # This acts as your master database for all Nigerian food
    return {
        "Swallows": ["Amala and Abula", "Pounded Yam and Egusi", "Eba and Okro", "Tuwo Masara"],
        "Rice": ["Jollof Rice", "Fried Rice", "White Rice and Ayamase"],
        "Proteins": ["Crispy Chicken", "Grilled Fish", "Peppered Snail", "Assorted Meat"],
        "Sides": ["Dodo Cubes", "Moin Moin", "Salad", "Coleslaw"]
    }

# --- Professional Personality (The Ibadan Local Expert) ---
SYSTEM_PROMPT = """
You are Ayo, the Lead Host at Chicken Republic Mokola. You are an expert on Ibadan geography and Nigerian cuisine.

CONVERSATIONAL RULES:
1. IBADAN EXPERT: You know all areas in Ibadan (Bodija, Akobo, Challenge, Oluyole, Iwo Road, Samonda, etc.). If a user mentions a location, acknowledge it (e.g., "Ah, Akobo! Our riders can get there fast via the new road.").
2. GENERAL KNOWLEDGE: Do not just talk about food. If the user asks about the weather in Ibadan, the best places to visit (like Agodi Gardens or Bowers Tower), or just wants to joke around, be a charming friend.
3. NIGERIAN MENU: You have access to a full Nigerian menu (Amala, Pounded Yam, Jollof, Ayamase, etc.). If they ask for something not on the basic menu, assume we can make it or suggest the closest match.
4. ORDER STRUCTURE: When they pick food:
   - Summarize: "You have ordered [Food]."
   - Order Number: "Your reference is CRM-[Random 5 Digits]."
   - Logistics: Ask "Is this for delivery to your location in Ibadan, or are you picking it up at our Mokola kitchen?"
   - Payment: "Please use the Checkout button. Let me know once paid so I can confirm it!"

TONE: Clear, professional English. Warm, witty, and very helpful.
"""

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "")
    menu = load_nigerian_menu()
    
    if 'history' not in session:
        session['history'] = []

    # Context includes the full menu for the AI to reference
    context = f"FULL NIGERIAN MENU: {menu}. LOCATION: Mokola, Ibadan (Expert in all Ibadan zones)."
    
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
                "temperature": 0.8,
                "max_tokens": 200 
            },
            timeout=10
        )
        ai_reply = response.json()['choices'][0]['message']['content']
        
        session['history'].append({"role": "user", "content": user_msg})
        session['history'].append({"role": "assistant", "content": ai_reply})
        session.modified = True
        
        return jsonify({"reply": ai_reply})
    except:
        return jsonify({"reply": "I'm sorry, I'm experiencing a small glitch. Can we try that again?"})

# --- Payment & Success (Standard) ---
@app.route("/initialize_payment", methods=["POST"])
def initialize_payment():
    order_data = request.json
    order_ref = f"CR-MOK-{random.randint(10000, 99999)}"
    payload = {
        "email": "customer@cr-mokola.com",
        "amount": int(order_data['amount']) * 100,
        "reference": order_ref,
        "callback_url": f"{MY_SITE_URL}/success",
        "metadata": {"location": order_data.get("location"), "cart": order_data.get("cart")}
    }
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
    try:
        res = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
        return jsonify(res.json())
    except: return jsonify({"status": False, "message": "Gateway busy"}), 500

@app.route("/success")
def success():
    ref = request.args.get('reference', 'ORDER-CONFIRMED')
    return render_template("success.html", order_id=ref)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
