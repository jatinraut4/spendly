import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from database.db import init_db, seed_db, create_user, verify_user, get_user_by_id
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
    get_monthly_spending_trend,
    insert_expense,
    get_expense_by_id,
    update_expense,
    delete_expense
)
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")


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

@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Fetch actual user data from database
    user_data = get_user_by_id(session["user_id"])
    if not user_data:
        session.clear()
        return redirect(url_for("login"))

    name_parts = user_data["name"].split()
    initials = "".join([part[0].upper() for part in name_parts if part])

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

    # Date Filter Logic (matching profile route)
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    parsed_from = None
    parsed_to = None

    if date_from:
        try:
            parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            date_from = None

    if date_to:
        try:
            parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            date_to = None

    if parsed_from and parsed_to and parsed_from > parsed_to:
        flash("Start date must be before end date.", "error")
        date_from = None
        date_to = None
        parsed_from = None
        parsed_to = None

    today = datetime.now().date()
    first_of_month = today.replace(day=1)
    three_months_ago = today - relativedelta(months=3)
    six_months_ago = today - relativedelta(months=6)

    preset_urls = {
        "this_month": url_for('analytics',
                              date_from=first_of_month.strftime('%Y-%m-%d'),
                              date_to=today.strftime('%Y-%m-%d')),
        "last_3_months": url_for('analytics',
                                  date_from=three_months_ago.strftime('%Y-%m-%d'),
                                  date_to=today.strftime('%Y-%m-%d')),
        "last_6_months": url_for('analytics',
                                  date_from=six_months_ago.strftime('%Y-%m-%d'),
                                  date_to=today.strftime('%Y-%m-%d')),
        "all_time": url_for('analytics')
    }

    active_preset = None
    if parsed_from and parsed_to:
        if parsed_from == first_of_month and parsed_to == today:
            active_preset = "this_month"
        elif parsed_from == three_months_ago and parsed_to == today:
            active_preset = "last_3_months"
        elif parsed_from == six_months_ago and parsed_to == today:
            active_preset = "last_6_months"
        else:
            active_preset = "custom"
    elif not parsed_from and not parsed_to:
        active_preset = "all_time"

    user_id = session["user_id"]
    stats = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    categories = get_category_breakdown(user_id, date_from=date_from, date_to=date_to)
    monthly_trend = get_monthly_spending_trend(user_id, date_from=date_from, date_to=date_to)

    return render_template(
        "analytics.html",
        user=user,
        stats=stats,
        categories=categories,
        monthly_trend=monthly_trend,
        date_from=date_from,
        date_to=date_to,
        active_preset=active_preset,
        preset_urls=preset_urls
    )


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

    # ========== Date Filter Logic ==========
    # Parse query parameters
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    # Validate dates (try-except with silent fallback)
    parsed_from = None
    parsed_to = None

    if date_from:
        try:
            parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            date_from = None

    if date_to:
        try:
            parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            date_to = None

    # Check if date_from > date_to (reversed range)
    if parsed_from and parsed_to and parsed_from > parsed_to:
        flash("Start date must be before end date.", "error")
        date_from = None
        date_to = None
        parsed_from = None
        parsed_to = None

    # Calculate preset URLs
    today = datetime.now().date()
    first_of_month = today.replace(day=1)
    three_months_ago = today - relativedelta(months=3)
    six_months_ago = today - relativedelta(months=6)

    preset_urls = {
        "this_month": url_for('profile',
                              date_from=first_of_month.strftime('%Y-%m-%d'),
                              date_to=today.strftime('%Y-%m-%d')),
        "last_3_months": url_for('profile',
                                  date_from=three_months_ago.strftime('%Y-%m-%d'),
                                  date_to=today.strftime('%Y-%m-%d')),
        "last_6_months": url_for('profile',
                                  date_from=six_months_ago.strftime('%Y-%m-%d'),
                                  date_to=today.strftime('%Y-%m-%d')),
        "all_time": url_for('profile')
    }

    # Determine active preset (for UI highlighting)
    active_preset = None
    if parsed_from and parsed_to:
        if parsed_from == first_of_month and parsed_to == today:
            active_preset = "this_month"
        elif parsed_from == three_months_ago and parsed_to == today:
            active_preset = "last_3_months"
        elif parsed_from == six_months_ago and parsed_to == today:
            active_preset = "last_6_months"
        else:
            active_preset = "custom"
    elif not parsed_from and not parsed_to:
        active_preset = "all_time"

    # Fetch filtered data from database
    user_id = session["user_id"]
    stats = get_summary_stats(user_id, date_from=date_from, date_to=date_to)
    transactions = get_recent_transactions(user_id, limit=10, date_from=date_from, date_to=date_to)
    categories = get_category_breakdown(user_id, date_from=date_from, date_to=date_to)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        date_from=date_from,
        date_to=date_to,
        active_preset=active_preset,
        preset_urls=preset_urls
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

    if request.method == "POST":
        amount_str = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_str = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        # Validation
        error = None
        amount = None

        if not amount_str:
            error = "Amount is required."
        else:
            try:
                amount = float(amount_str)
                if amount <= 0:
                    error = "Amount must be a positive number greater than 0."
            except ValueError:
                error = "Amount must be a valid number."

        if not error and not category:
            error = "Category is required."
        elif not error and category not in categories:
            error = "Invalid category selected."

        if not error and not date_str:
            error = "Date is required."
        elif not error:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                error = "Invalid date format. Use YYYY-MM-DD."

        if error:
            return render_template(
                "add_expense.html",
                categories=categories,
                error=error,
                form_data={
                    "amount": amount_str,
                    "category": category,
                    "date": date_str,
                    "description": description
                }
            )

        # Optional description handling
        desc_val = description if description else None

        try:
            insert_expense(session["user_id"], amount, category, date_str, desc_val)
            return redirect(url_for("profile"))
        except Exception as e:
            return render_template(
                "add_expense.html",
                categories=categories,
                error="An unexpected error occurred while saving the expense.",
                form_data={
                    "amount": amount_str,
                    "category": category,
                    "date": date_str,
                    "description": description
                }
            )

    today_date = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "add_expense.html",
        categories=categories,
        form_data={
            "date": today_date
        }
    )


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    expense = get_expense_by_id(id, user_id)
    if not expense:
        abort(404)

    categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

    if request.method == "POST":
        amount_str = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_str = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        error = None
        amount = None

        if not amount_str:
            error = "Amount is required."
        else:
            try:
                amount = float(amount_str)
                if amount <= 0:
                    error = "Amount must be a positive number greater than 0."
            except ValueError:
                error = "Amount must be a valid number."

        if not error and not category:
            error = "Category is required."
        elif not error and category not in categories:
            error = "Invalid category selected."

        if not error and not date_str:
            error = "Date is required."
        elif not error:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                error = "Invalid date format. Use YYYY-MM-DD."

        if error:
            return render_template(
                "edit_expense.html",
                expense=expense,
                categories=categories,
                error=error,
                form_data={
                    "amount": amount_str,
                    "category": category,
                    "date": date_str,
                    "description": description
                }
            )

        desc_val = description if description else None

        try:
            update_expense(id, user_id, amount, category, date_str, desc_val)
            return redirect(url_for("profile"))
        except Exception as e:
            return render_template(
                "edit_expense.html",
                expense=expense,
                categories=categories,
                error="An unexpected error occurred while updating the expense.",
                form_data={
                    "amount": amount_str,
                    "category": category,
                    "date": date_str,
                    "description": description
                }
            )

    return render_template(
        "edit_expense.html",
        expense=expense,
        categories=categories
    )


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense_route(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    expense = get_expense_by_id(id, user_id)
    if not expense:
        abort(404)

    delete_expense(id, user_id)
    return redirect(url_for("profile"))


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
