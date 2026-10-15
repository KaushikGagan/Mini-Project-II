# Email OTP Experiment — Developer Handoff

## Scope

Only OTP delivery changed. Registration verification, hashing, database storage, citizen login, admin login, and all application/certificate workflows remain unchanged.

## Modified files

- `requirements.txt` — adds `Flask-Mail`.
- `config.py` — SMTP configuration from environment variables.
- `.env.example` — documented Gmail SMTP variables.
- `backend/app/extensions.py` / `backend/app/__init__.py` — Flask-Mail extension initialization.
- `backend/app/services/otp_service.py` — stores generation timestamp and supports 60-second cooldown calculations.
- `backend/app/routes/auth.py` — email validation, SMTP delivery, failure handling, and no terminal OTP output.
- `backend/app/templates/auth/register.html` and `backend/app/static/js/app.js` — no-refresh Send/Resend OTP controls and countdown.

## Required local `.env` values

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-gmail-address@gmail.com
MAIL_PASSWORD=your-16-character-gmail-app-password
MAIL_DEFAULT_SENDER=your-gmail-address@gmail.com
```

`.env` is Git ignored. Never commit an App Password.

## Gmail manual setup

1. Enable 2-Step Verification for the Gmail account.
2. Create a Gmail **App Password** for Mail.
3. Copy the generated 16-character App Password to `MAIL_PASSWORD` in `.env`.
4. Restart Flask.

## Flow

1. Browser validates the email through Flask.
2. Flask creates a cryptographically secure six-digit OTP in the signed session, valid for 10 minutes.
3. Flask sends the OTP only in the email body.
4. No OTP is printed to the terminal or returned to JavaScript.
5. The page remains intact; form fields do not refresh.
6. Resend is denied by the server for 60 seconds. A successful resend creates a new OTP and invalidates the old one.
7. Successful registration removes the OTP session record as before.

## Testing

- Flask-Mail dependency installed.
- Compilation passed.
- Mock SMTP test passed for initial delivery, JSON success response without OTP leakage, server-side cooldown, and resend delivery invocation.
- Live Gmail delivery is pending the developer adding valid Gmail App Password settings to local `.env`.

## Rollback

This experiment is local only and has not been pushed to GitHub. If SMTP delivery is unsuitable, restore the previous `request_otp` route and front-end control, remove `Flask-Mail` from requirements, and remove the `MAIL_*` configuration entries.
