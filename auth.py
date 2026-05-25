import sqlite3, hashlib, os

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")
    # ADD THIS ↓
    conn.execute("""CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        chats TEXT NOT NULL DEFAULT '[]',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit(); conn.close()

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def signup(name, username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO users (name,username,password) VALUES (?,?,?)",
                     (name, username, hash_pw(password)))
        conn.commit(); conn.close()
        return {"name": name, "username": username}
    except sqlite3.IntegrityError:
        raise ValueError("Username already exists")

def login(username, password):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT name,username FROM users WHERE username=? AND password=?",
                       (username, hash_pw(password))).fetchone()
    conn.close()
    if not row: raise ValueError("Invalid username or password")
    return {"name": row[0], "username": row[1]}