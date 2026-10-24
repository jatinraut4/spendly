from flask import Flask, render_template, request, redirect, url_for, session
from database.db import init_db, seed_db, create_user
import sqlite3

app = Flask(__name__)


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


@app.route("/login")
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
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
    return "Logout — coming in Step 3"


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded data for Step 4 design validation
    user = {
        "name": "Jatin Raut",
        "email": "jatin@example.com",
        "initials": "JR",
        "joined_date": "October 2023"
    }
    stats = {
        "total_spent": "12,450",
        "count": 42,
        "top_category": "Food & Dining"
    }
    transactions = [
        {"date": "2023-10-20", "description": "Starbucks Coffee", "category": "Food", "category_class": "food", "amount": "350"},
        {"date": "2023-10-19", "description": "Uber Ride", "category": "Transport", "category_class": "transport", "amount": "120"},
        {"date": "2023-10-18", "description": "Netflix Subscription", "category": "Entertainment", "category_class": "entertainment", "amount": "499"},
        {"date": "2023-10-17", "description": "Grocery Store", "category": "Shopping", "category_class": "shopping", "amount": "2,100"},
    ]
    categories = [
        {"name": "Food & Dining", "amount": "5,200", "percentage": 42},
        {"name": "Transport", "amount": "3,100", "percentage": 25},
        {"name": "Shopping", "amount": "2,450", "percentage": 20},
        {"name": "Others", "amount": "1,700", "percentage": 13},
    ]

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
