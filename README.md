## CyberCafe Project – Current Status

This README summarizes the setup and the changes made during the current session so you (or any teammate) can pick up the work quickly.

---

### 1. Project Setup & Dependencies

- Python virtual environment created under `.venv` (via `uv`).
- Dependencies installed from `requirements.txt` (Django 5.2.7, django-daraja, DRF, etc.). `mysqlclient` is skipped locally unless system headers are available; SQLite acts as the default DB when `DATABASE_URL` is unset.
- `manage.py migrate` has been run; migrations up to `cyberapp.0005` are applied.
- Dev server is started with:

  ```bash
  cd cyber
  ../.venv/bin/python manage.py runserver 0.0.0.0:8000
  ```

---

### 2. Environment Configuration

`cyber/settings.py` loads `.env` from the project root (`cyber/.env`). Ensure this file contains at least:

```
SECRET_KEY=…
DEBUG=True

MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=…
MPESA_CONSUMER_SECRET=…
MPESA_SHORTCODE=174379
MPESA_EXPRESS_SHORTCODE=174379
MPESA_PASSKEY=…
MPESA_CALLBACK_URL=https://<public-domain>/mpesa/callback/
```

`MPESA_CALLBACK_URL` must match the public HTTPS endpoint that Safaricom calls (e.g., an ngrok tunnel hitting `/mpesa/callback/`).

---

### 3. STK Push Implementation (Summary)

More detail lives in `STK_SETUP.md`, but the highlights:

- Shared helper `_send_stk_request` in `cyberapp/views.py` validates phone/amount, calls `MpesaClient.stk_push`, and returns a JSON-compatible dict.
- **Session flow**: `/sessions/<id>/stk/` (AJAX from `active_sessions.html`) sends STK after a session ends, recording checkout IDs and payment status on `UsageSession`.
- **Payment flow**: `add_payment` view triggers STK when recording a payment; `Payment` model now tracks `mpesa_status`, checkout IDs, receipts, etc.
- `/mpesa/callback/` updates either a `UsageSession` or `Payment` based on `CheckoutRequestID`.
- `STK_SETUP.md` documents the exact code paths, troubleshooting tips, and ngrok instructions.

---

### 4. Key UI Updates

- Dashboard (`home.html`) now links to the new `summary_session` page and surfaces payment/session stats.
- Active Sessions page includes client-side timers, “End Session”, and “Send STK” buttons wired to the AJAX endpoints.
- Payments list shows real-time Mpesa status chips (Pending, Paid, Failed) and receipt numbers.
- A profile page template (`profile.html`) was added to resolve the missing template error.

---

### 5. Outstanding Items / Tips

1. **Mpesa credentials** – keep them out of version control; regenerate if they were shared publicly.
2. **Callback URL** – must be HTTPS and end with `/mpesa/callback/`. Safaricom rejects anything else.
3. **Testing** – use ngrok (or deploy) so Daraja can reach your callback, then watch the terminal for callback logs.
4. **Database** – if switching to MySQL/Postgres, set `DATABASE_URL` in `.env` and rerun migrations.

---

With the above in place, the project can:

- Manage students, sessions, and payments through the web UI.
- Compute session charges and push STK requests to customers’ phones.
- Track payment confirmations automatically via the Mpesa callback.

Refer to `STK_SETUP.md` for deeper code-level notes, and feel free to extend this README as new features land.

