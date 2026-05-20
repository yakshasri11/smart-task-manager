from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import psycopg2
import psycopg2.extras
from utils.analytics import compute_stats
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", logger=False, engineio_logger=False)

def get_db_connection():
    conn = psycopg2.connect(app.config["DATABASE_URL"])
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Please login first"}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("dashboard.html", username=session["username"])

@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/register")
def register_page():
    if "user_id" in session:
        return redirect(url_for("home"))
    return render_template("register.html")

@app.route("/api/auth/register", methods=["POST"])
def register():
    body = request.get_json()
    username = body.get("username", "").strip()
    email    = body.get("email", "").strip()
    password = body.get("password", "")
    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password should be at least 6 characters"}), 400
    pw_hash = generate_password_hash(password)
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id", (username, email, pw_hash))
        new_id = cur.fetchone()["id"]
        conn.commit()
        cur.close()
        conn.close()
        session["user_id"]  = new_id
        session["username"] = username
        return jsonify({"message": "Account created!", "username": username}), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "Email or username already taken"}), 409
    except Exception as e:
        print("Register error:", e)
        return jsonify({"error": "Something went wrong"}), 500

@app.route("/api/auth/login", methods=["POST"])
def login():
    body = request.get_json()
    email    = body.get("email", "").strip()
    password = body.get("password", "")
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Wrong email or password"}), 401
        session["user_id"]  = user["id"]
        session["username"] = user["username"]
        return jsonify({"message": "Login successful", "username": user["username"]}), 200
    except Exception as e:
        print("Login error:", e)
        return jsonify({"error": "Something went wrong"}), 500

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route("/api/tasks", methods=["GET"])
@login_required
def get_tasks():
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC", (session["user_id"],))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([dict(row) for row in rows]), 200
    except Exception as e:
        print("Get tasks error:", e)
        return jsonify({"error": "Failed to fetch tasks"}), 500

@app.route("/api/tasks", methods=["POST"])
@login_required
def create_task():
    body        = request.get_json()
    title       = body.get("title", "").strip()
    description = body.get("description", "").strip()
    priority    = body.get("priority", "medium")
    status      = body.get("status", "pending")
    if not title:
        return jsonify({"error": "Task title is required"}), 400
    if priority not in ["low", "medium", "high"]:
        return jsonify({"error": "Invalid priority"}), 400
    if status not in ["pending", "in_progress", "completed"]:
        return jsonify({"error": "Invalid status"}), 400
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(
            "INSERT INTO tasks (user_id, title, description, priority, status) VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (session["user_id"], title, description, priority, status)
        )
        task = dict(cur.fetchone())
        conn.commit()
        cur.close()
        conn.close()
        task["created_at"] = str(task["created_at"])
        socketio.emit("new_task", task)
        return jsonify(task), 201
    except Exception as e:
        print("Create task error:", e)
        return jsonify({"error": "Failed to create task"}), 500

@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
@login_required
def update_task(task_id):
    body    = request.get_json()
    allowed = ["title", "description", "priority", "status"]
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        return jsonify({"error": "Nothing to update"}), 400
    set_clause = ", ".join(f"{col} = %s" for col in updates)
    vals       = list(updates.values()) + [task_id, session["user_id"]]
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute(f"UPDATE tasks SET {set_clause} WHERE id = %s AND user_id = %s RETURNING *", vals)
        updated = cur.fetchone()
        if not updated:
            cur.close()
            conn.close()
            return jsonify({"error": "Task not found"}), 404
        updated = dict(updated)
        updated["created_at"] = str(updated["created_at"])
        conn.commit()
        cur.close()
        conn.close()
        socketio.emit("task_changed", updated)
        return jsonify(updated), 200
    except Exception as e:
        print("Update task error:", e)
        return jsonify({"error": "Failed to update task"}), 500

@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s RETURNING id", (task_id, session["user_id"]))
        deleted = cur.fetchone()
        if not deleted:
            cur.close()
            conn.close()
            return jsonify({"error": "Task not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        socketio.emit("task_removed", {"id": task_id})
        return jsonify({"message": "Task deleted"}), 200
    except Exception as e:
        print("Delete task error:", e)
        return jsonify({"error": "Failed to delete task"}), 500

@app.route("/api/analytics", methods=["GET"])
@login_required
def get_analytics():
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE user_id = %s", (session["user_id"],))
        all_tasks = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        stats = compute_stats(all_tasks)
        return jsonify(stats), 200
    except Exception as e:
        print("Analytics error:", e)
        return jsonify({"error": "Failed to compute analytics"}), 500

@socketio.on("connect")
def handle_connect():
    emit("welcome", {"msg": "Connected"})

@socketio.on("disconnect")
def handle_disconnect():
    pass

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, use_reloader=False, allow_unsafe_werkzeug=True)
