from flask import Flask, render_template, request, redirect, url_for, session
from database.db import init_db, seed_db, create_user, verify_user, get_user_by_id
from database.queries import get_summary_stats, get_recent_transactions, get_category_breakdown
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not name or not email or not password or not confirm_password:
            return render_template("register.html", error="All fields are required")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")

        try:
            create_user(name, email, password)
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Email address already registered")
        except Exception as e:
            return render_template("register.html", error="An unexpected error occurred. Please try again.")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            return render_template("login.html", error="Email and password are required")

        user = verify_user(email, password)
        if user:
            session["user_id"] = user["id"]
            return redirect(url_for("profile"))
        else:
            return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Fetch actual user data from database
    user_data = get_user_by_id(session["user_id"])
    if not user_data:
        session.clear()
        return redirect(url_for("login"))

    # Extract initials from name
    name_parts = user_data["name"].split()
    initials = "".join([part[0].upper() for part in name_parts if part])

    # Format joined date
    try:
        created_at = datetime.strptime(user_data["created_at"], "%Y-%m-%d %H:%M:%S")
        joined_date = created_at.strftime("%B %Y")
    except:
        joined_date = "Recently"

    user = {
        "name": user_data["name"],
        "email": user_data["email"],
        "initials": initials,
        "joined_date": joined_date
    }

    # Fetch real data from database
    user_id = session["user_id"]
    stats = get_summary_stats(user_id)
    transactions = get_recent_transactions(user_id, limit=10)
    categories = get_category_breakdown(user_id)

    return render_template("profile.html", user=user, stats=stats, transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
