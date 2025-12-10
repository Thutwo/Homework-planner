import sqlite3, hashlib, os

DB_FILE = "planner.db"

def conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    with conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt BLOB NOT NULL
        );
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            due TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """)

# --- password hashing helpers (PBKDF2) ---
def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return dk.hex()

def create_user(username: str, password: str) -> bool:
    salt = os.urandom(16)
    pwh = _hash_password(password, salt)
    try:
        with conn() as c:
            c.execute("INSERT INTO users(username, password_hash, salt) VALUES(?,?,?)",
                      (username, pwh, salt))
        return True
    except sqlite3.IntegrityError:
        return False  # username already exists

def verify_user(username: str, password: str):
    with conn() as c:
        row = c.execute("SELECT id, password_hash, salt FROM users WHERE username=?",
                        (username,)).fetchone()
    if not row:
        return None
    uid, pwh, salt = row
    if _hash_password(password, salt) == pwh:
        return uid
    return None

# --- task ops ---
def list_tasks(user_id: int):
    with conn() as c:
        return c.execute(
            "SELECT id, title, due, done FROM tasks WHERE user_id=? ORDER BY done, id",
            (user_id,)
        ).fetchall()

def add_task(user_id: int, title: str, due: str):
    with conn() as c:
        c.execute("INSERT INTO tasks(user_id, title, due, done) VALUES(?,?,?,0)",
                  (user_id, title, due))

def mark_done(user_id: int, task_id: int):
    with conn() as c:
        c.execute("UPDATE tasks SET done=1 WHERE id=? AND user_id=?", (task_id, user_id))
def delete_task(user_id: int, task_id: int):
    with conn() as c:
        c.execute(
            "DELETE FROM tasks WHERE user_id=? AND id=?",
            (user_id, task_id)
        )
def add_task_if_not_exists(user_id: int, title: str, due: str):
    """Insert a task only if a task with same title+due for this user does not exist."""
    with conn() as c:
        row = c.execute(
            "SELECT id FROM tasks WHERE user_id=? AND title=? AND due=?",
            (user_id, title, due)
        ).fetchone()
        if row is None:
            c.execute(
                "INSERT INTO tasks(user_id, title, due, done) VALUES(?,?,?,0)",
                (user_id, title, due)
            )
