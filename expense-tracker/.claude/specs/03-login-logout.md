---
# Spec: Login and Logout

## Overview
This feature implements the authentication mechanism for Spendly. It allows registered users to securely log into their accounts and manage their sessions via a logout function. This is a critical step to ensure that subsequent features (like profile management and expense tracking) are user-specific and secure.

## Depends on
- Step 2: User Registration

## Routes
- `GET /login` — Renders the login page — public
- `POST /login` — Validates credentials and starts session — public
- `GET /logout` — Ends the session and redirects to login — logged-in

## Database changes
No database changes. The `users` table already contains `email` and `password_hash`.

## Templates
- **Modify:** `login.html` — Add a form to handle POST requests and display error messages.

## Files to change
- `app.py` — Implement logic for `login` (POST) and `logout` routes.
- `database/db.py` — Add a helper function to fetch a user by email.
- `templates/login.html` — Update for form submission and error handling.

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (use `check_password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use Flask `session` to track logged-in users (store `user_id`)

## Definition of done
- [ ] A user can log in with a valid email and password.
- [ ] An invalid email or password results in an error message on the login page.
- [ ] After logging in, the user is redirected to the profile page (stub).
- [ ] A logged-in user can click "Logout" to clear their session and be redirected to the login page.
- [ ] Attempting to access `/logout` without being logged in redirects to `/login`.
---
