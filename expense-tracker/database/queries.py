from database.db import get_db


def format_amount(amount):
    """
    Format a numeric amount as a string with commas.
    Example: 12450.50 -> "12,450.50"
    """
    return f"{amount:,.2f}"


def get_summary_stats(user_id):
    """
    Calculate summary statistics for a user's expenses.
    Returns dict with total_spent, transaction_count, top_category.

    Edge case: If user has no expenses, returns:
    {"total_spent": "0.00", "transaction_count": 0, "top_category": "—"}
    """
    with get_db() as conn:
        # Get total and count
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as count FROM expenses WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        total_spent = row["total"]
        count = row["count"]

        # Get top category
        if count > 0:
            top_row = conn.execute(
                "SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
                (user_id,)
            ).fetchone()
            top_category = top_row["category"]
        else:
            top_category = "—"

        return {
            "total_spent": format_amount(total_spent),
            "count": count,
            "top_category": top_category
        }


def get_category_breakdown(user_id):
    """
    Calculate per-category spending breakdown with percentages.
    Returns list of dicts with name, amount, pct (percentage as integer).
    Percentages are adjusted to sum to exactly 100.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (user_id,)
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

def get_recent_transactions(user_id, limit=10):
    """
    Fetch recent transactions for a user, ordered newest-first.

    Args:
        user_id: The ID of the user whose transactions to fetch
        limit: Maximum number of transactions to return (default 10)

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
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT ?",
            (user_id, limit)
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
