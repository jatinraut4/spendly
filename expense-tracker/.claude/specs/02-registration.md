---
# Spec: Registration

## Overview
This feature implements the user registration process, allowing new users to create an account by providing their name, email, and password. This is a foundational step in the Spendly roadmap, enabling personalized expense tracking.

## Depends on
Step 1 (Database Setup)

## Routes
- `GET /register` — Render registration form — public
- `POST /register` — Process registration and create user account — public

## Database changes
No database changes. The `users` table already exists with `name`, `email`, and `password_hash`.

## Templates
- **Create:** None (existing `register.html` will be used)
- **Modify:** `templates/register.html` — Update form to use `POST` method and appropriate input names.

## Files to change
- `app.py` — Implement `POST /register` logic.
- `templates/register.html` — Update form for submission.
- `database/db.py` — Add helper function to create a user.

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate that email is not already registered; return a clear error message if it is.
- Redirect to `/login` upon successful registration.

## Definition of done
- [ ] Navigating to `/register` renders the registration page.
- [ ] Submitting the form with valid data creates a new record in the `users` table.
- [ ] Passwords stored in the database are hashed and not plain text.
- [ ] Attempting to register with an existing email produces an error message.
- [ ] Successful registration redirects the user to the login page.
---
