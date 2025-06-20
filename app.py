from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import sqlite3
import cohere

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Initialize Cohere client
co = cohere.Client("4GTzqZ8iZrLTzJW1czAzQvzN763pSgNSuNAPWHY5")  # Replace with your actual Cohere API key

SYSTEM_PROMPT = """You are LawBot, an Indian legal expert.
For each question:
1. Explain the situation clearly.
2. Mention IPC/CrPC or other relevant laws.
3. Keep it short, fact-based, and understandable.
4. At last provide: What You Can Do:
5. complete the sentence you are talking
"""

# ----- DB Setup -----
def init_db():
    conn = sqlite3.connect('forum.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT,
            votes INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# ----- ROUTES -----

@app.route("/")
def home():
    return render_template("chatbot.html")  # Use chatbot as landing page

@app.route("/forum")
def index():
    conn = sqlite3.connect('forum.db')
    c = conn.cursor()
    c.execute("SELECT * FROM posts ORDER BY votes DESC, id DESC")
    posts = c.fetchall()
    conn.close()
    return render_template('index.html', posts=posts)

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("query", "")
    if not user_input.strip():
        return jsonify({"response": "Please provide a valid legal question."})
    
    response = co.chat(
        model="command-r-plus",
        message=user_input,
        temperature=0.7,
        max_tokens=300,
        chat_history=[],
        preamble=SYSTEM_PROMPT
    )
    return jsonify({"response": response.text.strip().replace("\n", "<br>")})
@app.route('/answer/<int:id>', methods=['POST'])
def answer(id):
    answer = request.form['answer']
    conn = sqlite3.connect('forum.db')
    c = conn.cursor()
    c.execute("UPDATE posts SET answer = ? WHERE id = ?", (answer, id))
    conn.commit()
    conn.close()
    return redirect('/forum')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin123':
            session['admin'] = True
            return redirect('/forum')
        flash("Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/forum')

@app.route('/post', methods=['GET', 'POST'])
def post():
    if request.method == 'POST':
        question = request.form['question']
        conn = sqlite3.connect('forum.db')
        c = conn.cursor()
        c.execute("INSERT INTO posts (question) VALUES (?)", (question,))
        conn.commit()
        conn.close()
        return redirect('/forum')
    return render_template('post.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if not session.get('admin'):
        return redirect('/login')
    conn = sqlite3.connect('forum.db')
    c = conn.cursor()
    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer']
        c.execute("UPDATE posts SET question=?, answer=? WHERE id=?", (question, answer, id))
        conn.commit()
        conn.close()
        return redirect('/forum')
    c.execute("SELECT * FROM posts WHERE id=?", (id,))
    post = c.fetchone()
    conn.close()
    return render_template('edit.html', post=post)

@app.route('/delete/<int:id>')
def delete(id):
    if not session.get('admin'):
        return redirect('/login')
    conn = sqlite3.connect('forum.db')
    c = conn.cursor()
    c.execute("DELETE FROM posts WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/forum')

@app.route('/vote/<int:id>/<action>')
def vote(id, action):
    conn = sqlite3.connect('forum.db')
    c = conn.cursor()
    if action == 'up':
        c.execute("UPDATE posts SET votes = votes + 1 WHERE id=?", (id,))
    elif action == 'down':
        c.execute("UPDATE posts SET votes = votes - 1 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/forum')

# ----- Start App -----
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
