from cs50 import SQL
from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required
from hardware import open_barrier

# Chat GPT helped with these imports to build a working admin page
import secrets
import string

# And these to build the barrier cooldown timer
import threading
import time


# Configure application
app = Flask(__name__)


# Load secret key used to protect Flask sessions
with open("secret_key.txt") as file:
    app.config["SECRET_KEY"] = file.read().strip()


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///smartblock.db")

# AI assistance: ChatGPT helped me use a Flask context processor
# to make admin status available to the shared navigation template.
@app.context_processor
def inject_admin_status():
    """Make admin status available to all templates."""

    if session.get("user_id"):
        user = db.execute(
            "SELECT is_admin FROM users WHERE id = ?",
            session["user_id"]
        )

        if user:
            return {"is_admin": user[0]["is_admin"]}

    return {"is_admin": False}


# AI assistance: ChatGPT helped me implement a thread-safe global cooldown
# so simultaneous users cannot trigger the barrier more than once within 5 seconds.
BARRIER_COOLDOWN_SECONDS = 5
last_barrier_open_time = None
barrier_lock = threading.Lock()


# MAIN PAGE
@app.route("/")
@login_required
def index():
    cooldown = request.args.get("cooldown")
    return render_template("index.html", cooldown=cooldown)

# LOG IN
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    session.clear()

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?",
            request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("Invalid username and/or password", 403)

        # Make sure user's account is active
        if not rows[0] ["is_active"]:
            return apology("This account is disabled", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Require residents using a temporary password to create their own password
        if rows[0]["must_change_password"]:
            return redirect("/change-password")

        return redirect("/")

    else:
        return render_template("login.html")


# LOG OUT
@app.route("/logout")
def logout():
    """Log user out"""

    session.clear()

    return redirect("/")


# ADMIN PAGE
@app.route("/admin")
@login_required
def admin():
    """Admin page"""

    # Make sure logged-in user is an admin
    current_user = db.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        session["user_id"]
    )

    if not current_user[0]["is_admin"]:
        return apology("Admin access required", 403)

    return render_template("admin.html")


# CREATE RESIDENT PAGE
@app.route("/admin/create", methods=["GET", "POST"])
@login_required
def admin_create():
    """Create resident account"""

    current_user = db.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        session["user_id"]
    )

    if not current_user[0]["is_admin"]:
        return apology("Admin access required", 403)

    temporary_password = None
    new_username = None

    if request.method == "POST":
        name = request.form.get("name")
        username = request.form.get("username")
        apartment = request.form.get("apartment")

        if not name or not username:
            return apology("Name and username are required", 400)

        # AI assistance: ChatGPT helped me implement random temporary password generation.
        alphabet = string.ascii_letters + string.digits
        temporary_password = "".join(secrets.choice(alphabet) for _ in range(10))

        hashed_password = generate_password_hash(
            temporary_password,
            method="pbkdf2:sha256"
        )

        db.execute(
            """
            INSERT INTO users
            (name, username, hash, apartment, is_admin, must_change_password)
            VALUES (?, ?, ?, ?, 0, 1)
            """,
            name,
            username,
            hashed_password,
            apartment
        )

        new_username = username

    return render_template(
        "admin_create.html",
        temporary_password=temporary_password,
        new_username=new_username
    )


# USERS PAGE
@app.route("/admin/users")
@login_required
def admin_users():
    """Manage resident accounts"""

    current_user = db.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        session["user_id"]
    )

    if not current_user[0]["is_admin"]:
        return apology("Admin access required", 403)

    users = db.execute(
    "SELECT * FROM users WHERE is_deleted = 0"
    )

    return render_template("admin_users.html", users=users)


# ADMIN HISTORY PAGE
@app.route("/admin/history")
@login_required
def admin_history():
    """Show all barrier opening history"""

    current_user = db.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        session["user_id"]
    )

    if not current_user[0]["is_admin"]:
        return apology("Admin access required", 403)

    all_events = db.execute(
        """
        SELECT datetime(events.timestamp, '+5 hours') AS timestamp,
        users.name, users.username, users.apartment
        FROM events
        JOIN users ON events.user_id = users.id
        ORDER BY events.timestamp DESC
        LIMIT 50
        """
    )

    return render_template(
        "admin_history.html",
        all_events=all_events
    )


# 


# CHANGE PASSWORD PAGE
@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change password"""

    if request.method == "GET":
        return render_template("change_password.html")

    password = request.form.get("password")
    confirmation = request.form.get("confirmation")

    if not password:
        return apology("Must provide new password", 400)

    if not confirmation:
        return apology("Must confirm new password", 400)

    if password != confirmation:
        return apology("Passwords must match", 400)

    hashed_password = generate_password_hash(
        password,
        method="pbkdf2:sha256"
    )

    db.execute(
        """
        UPDATE users
        SET hash = ?, must_change_password = 0
        WHERE id = ?
        """,
        hashed_password,
        session["user_id"]
    )

    return redirect("/")


# BARRIER OPENING
@app.route("/open", methods=["POST"])
@login_required
def open_barrier_route():
    """Open barrier"""

    global last_barrier_open_time

    # Make sure user's account is still active
    user = db.execute(
        "SELECT is_active FROM users WHERE id = ?",
        session["user_id"]
    )

    if not user[0]["is_active"]:
        session.clear()
        return redirect("/login")

    # Check global barrier cooldown
    with barrier_lock:
        current_time = time.monotonic()

        if last_barrier_open_time is not None:
            seconds_since_last_open = current_time - last_barrier_open_time

            if seconds_since_last_open < BARRIER_COOLDOWN_SECONDS:
                return apology("Please wait before opening the barrier again", 400)

        last_barrier_open_time = current_time

    # Send command to barrier hardware
    open_barrier()

    # Save opening event
    db.execute(
        "INSERT INTO events (user_id) VALUES (?)",
        session["user_id"]
    )

    return redirect("/?cooldown=5")


# SETTINGS PAGE
@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Change password"""

    if request.method == "GET":
        return render_template("settings.html")

    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirmation = request.form.get("confirmation")

    if not current_password or not new_password or not confirmation:
        return apology("Must complete all fields", 400)

    if new_password != confirmation:
        return apology("New passwords must match", 400)

    user = db.execute(
        "SELECT hash FROM users WHERE id = ?",
        session["user_id"]
    )

    if not check_password_hash(user[0]["hash"], current_password):
        return apology("Current password is incorrect", 403)

    new_hash = generate_password_hash(
        new_password,
        method="pbkdf2:sha256"
    )

    db.execute(
        "UPDATE users SET hash = ? WHERE id = ?",
        new_hash,
        session["user_id"]
    )

    return redirect("/")


# HISTORY PAGE
@app.route("/history")
@login_required
def history():
    """Show barrier opening history"""

    current_user = db.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        session["user_id"]
    )

    if current_user[0]["is_admin"]:
        events = db.execute(
            """
            SELECT datetime(events.timestamp, '+5 hours') AS timestamp, 
            users.name, users.apartment
            FROM events
            JOIN users ON events.user_id = users.id
            ORDER BY events.timestamp DESC
            LIMIT 50
            """
        )

    else:
        events = db.execute(
            """
            SELECT datetime(events.timestamp, '+5 hours') AS timestamp,
            users.name,
            users.apartment
            FROM events
            JOIN users ON events.user_id = users.id
            WHERE events.user_id = ?
            ORDER BY events.timestamp DESC
            LIMIT 50
            """,
            session["user_id"]
        )

    return render_template("history.html", events=events)


# USER DE/ACTIVATION
@app.route("/admin/toggle-user", methods=["POST"])
@login_required
def toggle_user():
    """Enable or disable resident access"""

    # Make sure logged-in user is an admin
    current_user = db.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        session["user_id"]
    )

    if not current_user[0]["is_admin"]:
        return apology("Admin access required", 403)

    user_id = request.form.get("user_id")

    user = db.execute(
        "SELECT is_active FROM users WHERE id = ?",
        user_id
    )

    new_status = 0 if user[0]["is_active"] else 1

    db.execute(
        "UPDATE users SET is_active = ? WHERE id = ?",
        new_status,
        user_id
    )

    return redirect("/admin/users")


# USER DELETION
@app.route("/admin/delete-user", methods=["POST"])
@login_required
def delete_user():
    """Soft delete resident account"""

    # Make sure logged-in user is an admin
    current_user = db.execute(
        "SELECT is_admin FROM users WHERE id = ?",
        session["user_id"]
    )

    if not current_user[0]["is_admin"]:
        return apology("Admin access required", 403)

    user_id = request.form.get("user_id")

    db.execute(
        """
        UPDATE users
        SET is_deleted = 1, is_active = 0
        WHERE id = ?
        """,
        user_id
    )

    return redirect("/admin/users")