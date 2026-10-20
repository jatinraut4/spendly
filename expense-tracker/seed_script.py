
import random
import sys
from datetime import datetime, timedelta
from database.db import get_db

def seed_expenses(user_id, count, months):
    categories_config = {
        'Food': {'range': (50, 800), 'weight': 30, 'desc': ['Street food', 'Grocery', 'Restaurant dinner', 'Tea and snacks', 'Lunch box']},
        'Transport': {'range': (20, 500), 'weight': 20, 'desc': ['Auto rickshaw', 'Petrol', 'Cab ride', 'Metro recharge', 'Bus fare']},
        'Bills': {'range': (200, 3000), 'weight': 15, 'desc': ['Electricity bill', 'Water bill', 'Internet recharge', 'Mobile bill', 'Rent']},
        'Health': {'range': (100, 2000), 'weight': 5, 'desc': ['Pharmacy', 'Doctor consultation', 'Medical tests', 'Supplements']},
        'Entertainment': {'range': (100, 1500), 'weight': 5, 'desc': ['Movie ticket', 'Gaming zone', 'OTT subscription', 'Concert']},
        'Shopping': {'range': (200, 5000), 'weight': 15, 'desc': ['Clothing', 'Electronics', 'Footwear', 'Home decor', 'Gift']},
        'Other': {'range': (50, 1000), 'weight': 10, 'desc': ['Stationery', 'Laundry', 'Misc expense', 'Tips']},
    }

    cat_list = list(categories_config.keys())
    weights = [categories_config[c]['weight'] for c in cat_list]

    expenses = []
    now = datetime.now()

    for _ in range(count):
        cat = random.choices(cat_list, weights=weights)[0]
        config = categories_config[cat]

        amount = round(random.uniform(*config['range']), 2)
        description = random.choice(config['desc'])

        # Random date within the past 'months' months
        days_back = random.randint(0, months * 30)
        date = (now - timedelta(days=days_back)).strftime('%Y-%m-%d')

        expenses.append((user_id, amount, cat, date, description))

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                expenses
            )
            conn.commit()

            # Get range for confirmation
            dates = [e[3] for e in expenses]
            date_range = f"{min(dates)} to {max(dates)}"

            # Get a sample of 5
            sample = conn.execute(
                "SELECT amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 5",
                (user_id,)
            ).fetchall()

            print(f"SUCCESS: {count} expenses inserted.")
            print(f"Date range: {date_range}")
            print("\nSample records:")
            for row in sample:
                # Using 'Rs.' instead of the Rupee symbol to avoid encoding issues in some terminals
                print(f"Rs.{row['amount']} | {row['category']} | {row['date']} | {row['description']}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Arguments from user input: user_id=2, count=5, months=3
    seed_expenses(2, 5, 3)
