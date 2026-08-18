from functools import wraps

from flask import redirect, render_template, session


def login_required(f):
    """Require user to be logged in."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def apology(message, code=400):
    """Render message as an apology to user."""
    return render_template("apology.html", message=message, code=code), code