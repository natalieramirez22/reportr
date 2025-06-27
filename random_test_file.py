from flask import Flask, request, render_template_string
import sqlite3
import html

app = Flask(__name__)

# CWE-89: SQL Injection (bad)
def get_user_bad(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

# CWE-89: SQL Injection (good)
def get_user_good(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    return cursor.fetchone()

# CWE-79: XSS (bad)
@app.route('/greet_bad')
def greet_bad():
    name = request.args.get('name', '')
    return f"<h1>Hello {name}</h1>"

# CWE-79: XSS (good)
@app.route('/greet_good')
def greet_good():
    name = request.args.get('name', '')
    safe_name = html.escape(name)
    return f"<h1>Hello {safe_name}</h1>"

# CWE-798: Hardcoded credentials (bad)
def connect_to_service():
    api_key = "SECRET_API_KEY_123"  # hardcoded secret
    return f"Connecting with key: {api_key}"

# CWE-327: Use of weak crypto (bad)
def weak_hash(password):
    import hashlib
    return hashlib.md5(password.encode()).hexdigest()

# CWE-916: Use of weak random number generator (bad)
def generate_token():
    import random
    return str(random.randint(100000, 999999))

@app.route('/')
def index():
    return render_template_string("""
        <h2>Security Demo</h2>
        <ul>
            <li><a href="/greet_bad?name=Jade">Greet (XSS - Bad)</a></li>
            <li><a href="/greet_good?name=Jade">Greet (XSS - Good)</a></li>
        </ul>
    """)

if __name__ == '__main__':
    app.run(debug=True)
# This code is a simple Flask application that demonstrates various security vulnerabilities.
# It includes examples of SQL Injection, Cross-Site Scripting (XSS), hardcoded