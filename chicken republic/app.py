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

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY")
MY_SITE_URL = "https://chicken-republic-r4bk.onrender.com" 
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- Fine-Tuned Rules ---
SYSTEM_PROMPT = """
You are Ahmad, the host at Chicken Republic Mokola. 
STRICT RULES:
1. MAX LENGTH: 2 short sentences only. No essays.
2. LANGUAGE: Clear, professional English. No broken English.
3. ORDERING: If they mention food, say "Great choice!" and ask "Would you like anything else to go with that, or are you ready for your payment link?"
4. PAYMENT TRIGGER: Do NOT suggest the payment link until the user says they are ready, done, or finished.
5. KNOWLEDGE: You know all Ibadan areas. Be friendly and witty.
"""

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data.get("message", "").lower()
    
    if 'history' not in session:
        session['history'] = []

    # --- NEW Logic: Only trigger link when user is READY ---
    ready_keywords = ["ready", "checkout", "that is all", "done", "finished", "pay now", "no more"]
    payment_link = None
    order_id = f"CRM-{random.randint(10000, 99999)}"

    if any(word in user_msg for word in ready_keywords):
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
        payload = {
            "email": "customer@cr-mokola.com",
            "amount": 2500 * 100, 
            "reference": order_id,
            "callback_url": f"{MY_SITE_URL}/success"
        }
        try:
            r = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
            res_data = r.json()
            if res_data.get('status'):
                payment_link = res_data['data']['authorization_url']
        except:
            pass

    # AI API Call
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
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
                "max_tokens": 80 # STOPS LONG REPLIES
            },
            timeout=10
        )
        ai_reply = response.json()['choices'][0]['message']['content']
        
        session['history'].append({"role": "user", "content": user_msg})
        session['history'].append({"role": "assistant", "content": ai_reply})
        session.modified = True
        
        return jsonify({
            "reply": ai_reply,
            "payment_link": payment_link,
            "order_id": order_id
        })
    except:
        return jsonify({"reply": "Network glitch, try again!"})

@app.route("/success")
def success():
    ref = request.args.get('reference', 'CRM-PRO-ORDER')
    return render_template("success.html", order_id=ref)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
