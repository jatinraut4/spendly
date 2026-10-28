## Overview
This pull request implements **Step 7: Add Expense** for Spendly and updates the **Analytics** page to a polished "Coming Soon" design matching Figma specifications.

### Changes Included:
- **Database Helper**: Added `insert_expense(user_id, amount, category, date, description)` in `database/queries.py` using secure parameterized queries.
- **Routes**: Implemented full `GET` and `POST` handlers for `/expenses/add` in `app.py`:
  - Authentication guards redirecting unauthenticated users to `/login`.
  - Input validation for amount (positive number > 0), fixed categories, valid `YYYY-MM-DD` date, and optional description.
  - Re-rendering form with pre-filled inputs and error messages on validation failure.
  - Redirecting to `/profile` on successful creation.
- **Templates & UI**:
  - Created `templates/add_expense.html` extending `base.html`.
  - Added "Add Expense" button/links to profile page and navigation bar.
  - Implemented Figma-designed "Coming Soon" page for `/analytics`.
- **Testing**:
  - Added comprehensive test suites (`tests/test_add_expense.py`, `tests/test_07-add-expense.py`) covering all unit logic and route integration cases.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
