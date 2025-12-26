from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import os
import json
import requests

app = Flask(__name__)

# --- Configuration ---
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

LLAMA_API_KEY = os.environ.get("GROQ_API_KEY")
LLAMA_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- System Prompt for Personality ---
SYSTEM_PROMPT = """
You are the friendly, energetic AI host for Chicken Republic Mokola.
Personality: Warm, helpful, and use light Nigerian slang (e.g., 'How body?', 'Enjoy your meal o!').
Rules:
1. Always be polite and answering any question the user has, even if it's not about chicken.
2. Use the provided Menu data for specific price questions.
3. Suggest the 'Refuel Meal' or 'Dodo Cubes' if they are unsure.
4. Keep responses concise and formatted for a chat bubble.
"""

def get_branch_data():
    try:
        with open("branch_data.json", "r") as f:
            return json.load(f)["branches"]["mokola"]
    except: return {"name": "Chicken Republic", "menu": []}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    branch = get_branch_data()
    
    if 'history' not in session:
        session['history'] = []

    # Build context for AI
    context = f"Branch Info: {branch['name']} in {branch.get('address', 'Ibadan')}. Menu: {branch['menu']}"
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n" + context}]
    messages.extend(session['history'][-6:]) # Remember last 3 exchanges
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
