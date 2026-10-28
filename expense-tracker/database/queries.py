from database.db import get_db


def format_amount(amount):
    """
    Format a numeric amount as a string with commas.
    Example: 12450.50 -> "12,450.50"
    """
    return f"{amount:,.2f}"


def get_summary_stats(user_id, date_from=None, date_to=None):
    """
    Calculate summary statistics for a user's expenses.
    Optionally filtered by date range.

    Args:
        user_id: The user's ID
        date_from: Optional start date (YYYY-MM-DD string, inclusive)
        date_to: Optional end date (YYYY-MM-DD string, inclusive)

    Returns dict with total_spent, count, top_category.

    Edge case: If user has no expenses, returns:
    {"total_spent": "0.00", "count": 0, "top_category": "—"}
    """
    with get_db() as conn:
        # Build WHERE clause conditionally
        where_clause = "WHERE user_id = ?"
        params = [user_id]

        if date_from and date_to:
            where_clause += " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])

        # Get total and count
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count FROM expenses " + where_clause,
            params
        ).fetchone()

        total_spent = row["total"]
        count = row["count"]

        # Get top category
        if count > 0:
            top_row = conn.execute(
                "SELECT category FROM expenses " + where_clause + " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
                params
            ).fetchone()
            top_category = top_row["category"]
        else:
            top_category = "—"

        return {
            "total_spent": format_amount(total_spent),
            "count": count,
            "top_category": top_category
        }


def get_category_breakdown(user_id, date_from=None, date_to=None):
    """
    Calculate per-category spending breakdown with percentages.
    Optionally filtered by date range.

    Args:
        user_id: The user's ID
        date_from: Optional start date (YYYY-MM-DD string, inclusive)
        date_to: Optional end date (YYYY-MM-DD string, inclusive)

    Returns list of dicts with name, amount, percentage (percentage as integer).
    Percentages are adjusted to sum to exactly 100.
    """
    with get_db() as conn:
        # Build WHERE clause conditionally
        where_clause = "WHERE user_id = ?"
        params = [user_id]

        if date_from and date_to:
            where_clause += " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])

        rows = conn.execute(
            "SELECT category, SUM(amount) as total FROM expenses "
            + where_clause
            + " GROUP BY category ORDER BY total DESC",
            params
        ).fetchall()

        if not rows:
            return []

        # Calculate total for percentages
        grand_total = sum(row["total"] for row in rows)

        # Build result with rounded percentages
        categories = []
        for row in rows:
            pct = round((row["total"] / grand_total) * 100)
            categories.append({
                "name": row["category"],
                "amount": format_amount(row["total"]),
                "percentage": pct
            })

        # Adjust largest category to make percentages sum to 100
        pct_sum = sum(c["percentage"] for c in categories)
        if pct_sum != 100 and categories:
            categories[0]["percentage"] += (100 - pct_sum)

        return categories

def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """
    Fetch recent transactions for a user, ordered newest-first.
    Optionally filtered by date range.

    Args:
        user_id: The ID of the user whose transactions to fetch
        limit: Maximum number of transactions to return (default 10)
        date_from: Optional start date (YYYY-MM-DD string, inclusive)
        date_to: Optional end date (YYYY-MM-DD string, inclusive)

    Returns:
        List of dicts, each containing:
        - date: YYYY-MM-DD string
        - description: Transaction description
        - category: Expense category
        - category_class: CSS class for category badge
        - amount: Formatted amount string with commas (e.g., "1,234.50")

        Returns empty list if no expenses exist.
    """
    with get_db() as conn:
        # Build WHERE clause conditionally
        where_clause = "WHERE user_id = ?"
        params = [user_id]

        if date_from and date_to:
            where_clause += " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])

        params.append(limit)

        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses " + where_clause + " ORDER BY date DESC LIMIT ?",
            params
        ).fetchall()

        return [
            {
                "date": row["date"],
                "description": row["description"],
                "category": row["category"],
                "category_class": row["category"].lower(),
                "amount": format_amount(row["amount"])
            }
            for row in rows
        ]


def get_monthly_spending_trend(user_id, date_from=None, date_to=None):
    """
    Fetch monthly spending aggregated by month (YYYY-MM), optionally filtered by date range.
    Returns list of dicts with month (e.g. '2026-10', or formatted label like 'Oct 2026') and amount.
    """
    with get_db() as conn:
        where_clause = "WHERE user_id = ?"
        params = [user_id]

        if date_from and date_to:
            where_clause += " AND date BETWEEN ? AND ?"
            params.extend([date_from, date_to])

        query = f"""
            SELECT strftime('%Y-%m', date) as month_key, SUM(amount) as total
            FROM expenses
            {where_clause}
            GROUP BY month_key
            ORDER BY month_key ASC
        """
        rows = conn.execute(query, params).fetchall()

        result = []
        for row in rows:
            month_key = row["month_key"]
            try:
                dt = datetime.strptime(month_key, "%Y-%m")
                label = dt.strftime("%b %Y")
            except:
                label = month_key

            result.append({
                "month": label,
                "month_key": month_key,
                "amount": format_amount(row["total"]),
                "raw_amount": row["total"]
            })
        return result
