from flask import Flask, request, jsonify, session
from flask_cors import CORS
import sqlite3
import bcrypt
import random
import string
import re

app = Flask(__name__)
app.secret_key = "secret123"
CORS(app, supports_credentials=True)

DB = "database.db"

# ------------------- DATABASE CONNECTION -------------------
def get_db():
    return sqlite3.connect(DB)

# ------------------- ENSURE TABLES & COLUMNS -------------------
def ensure_columns():
    con = get_db()
    cur = con.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            username TEXT UNIQUE,
            email TEXT,
            password BLOB,
            role TEXT
        )
    """)

    # Ensure missing columns for old DBs
    cur.execute("PRAGMA table_info(users)")
    existing_cols = [col[1] for col in cur.fetchall()]
    if 'fullname' not in existing_cols:
        cur.execute("ALTER TABLE users ADD COLUMN fullname TEXT")
        print("Added 'fullname' column")
    if 'email' not in existing_cols:
        cur.execute("ALTER TABLE users ADD COLUMN email TEXT")
        print("Added 'email' column")

    # Academics table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS academics(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            semester INTEGER,
            subject TEXT,
            marks INTEGER,
            attendance INTEGER
        )
    """)
    con.commit()
    con.close()

# ------------------- INIT DB ROUTE -------------------
@app.route("/init")
def init_db():
    ensure_columns()
    return "Database Initialized Successfully"

# ------------------- REGISTER -------------------
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.json
        fullname = data.get("fullname")
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")

        # Field validation
        if not fullname or not username or not email or not password or not role:
            return jsonify({"message": "All fields are required!"})

        if len(username) < 3 or len(username) > 100:
            return jsonify({"message": "Username must be 3-100 characters!"})

        if len(password) < 6 or len(password) > 20 or not re.search(r"[A-Za-z]", password) \
           or not re.search(r"[0-9]", password) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return jsonify({"message": "Password must include letters, numbers, and a special character (6-20 chars)!"})

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({"message": "Invalid email format!"})

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username=? OR email=?", (username, email))
        if cur.fetchone():
            return jsonify({"message": "Username or email already exists!"})

        cur.execute("INSERT INTO users(fullname, username, email, password, role) VALUES(?,?,?,?,?)",
                    (fullname, username, email, hashed, role))
        con.commit()
        con.close()
        return jsonify({"message": "Registered Successfully"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"})

# ------------------- LOGIN -------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT password, role FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    con.close()

    if user and bcrypt.checkpw(password.encode(), user[0]):
        session["username"] = username
        session["role"] = user[1]
        return jsonify({"message": "Login Success", "role": user[1]})
    return jsonify({"message": "Invalid Credentials"})

# ------------------- LOGOUT -------------------
@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

# ------------------- FORGOT PASSWORD / USERNAME -------------------
@app.route("/forgot", methods=["POST"])
def forgot():
    data = request.json
    type_ = data.get("type")
    username = data.get("username")
    email = data.get("email")
    newvalue = data.get("newvalue")
    confirmvalue = data.get("confirmvalue")
    captcha = data.get("captcha")
    captcha_real = data.get("captcha_real")

    if captcha != captcha_real:
        return jsonify({"message": "Captcha mismatch!"})
    if newvalue != confirmvalue:
        return jsonify({"message": "New value and confirm value do not match!"})

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND email=?", (username, email))
    user = cur.fetchone()
    if not user:
        return jsonify({"message": "User not found!"})

    if type_ == "password":
        hashed = bcrypt.hashpw(newvalue.encode(), bcrypt.gensalt())
        cur.execute("UPDATE users SET password=? WHERE username=?", (hashed, username))
    elif type_ == "username":
        cur.execute("SELECT * FROM users WHERE username=?", (newvalue,))
        if cur.fetchone():
            return jsonify({"message": "New username already exists!"})
        cur.execute("UPDATE users SET username=? WHERE id=?", (newvalue, user[0]))
    else:
        return jsonify({"message": "Invalid type!"})

    con.commit()
    con.close()
    return jsonify({"message": f"{type_.capitalize()} updated Successfully"})

# ------------------- CAPTCHA -------------------
@app.route("/captcha")
def captcha():
    code = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
    return jsonify({"captcha": code})

# ------------------- STUDENT DASHBOARD DATA -------------------
@app.route("/student/data")
def student_data():
    if session.get("role") != "student":
        return jsonify([])
    username = session.get("username")
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT semester, subject, marks, attendance FROM academics WHERE username=?", (username,))
    data = [{"semester": r[0], "subject": r[1], "marks": r[2], "attendance": r[3]} for r in cur.fetchall()]
    con.close()
    return jsonify(data)

# ------------------- FACULTY DASHBOARD DATA -------------------
@app.route("/faculty/data")
def faculty_data():
    if session.get("role") != "faculty":
        return jsonify([])
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT username, semester, subject, marks, attendance FROM academics")
    data = [{"username": r[0], "semester": r[1], "subject": r[2], "marks": r[3], "attendance": r[4]} for r in cur.fetchall()]
    con.close()
    return jsonify(data)

# ------------------- FACULTY ADD RECORD -------------------
@app.route("/faculty/update", methods=["POST"])
def faculty_update():
    if session.get("role") != "faculty":
        return jsonify({"message": "Unauthorized"})
    data = request.json
    username = data.get("username")
    semester = data.get("semester")
    subject = data.get("subject")
    marks = data.get("marks")
    attendance = data.get("attendance")

    con = get_db()
    cur = con.cursor()
    cur.execute("INSERT INTO academics(username, semester, subject, marks, attendance) VALUES(?,?,?,?,?)",
                (username, semester, subject, marks, attendance))
    con.commit()
    con.close()
    return jsonify({"message": "Record added Successfully"})

# ------------------- RUN APP -------------------
if __name__ == "__main__":
    ensure_columns()
    app.run(debug=True)