# STK Push Integration Guide

This project uses **django-daraja** to send M-Pesa STK prompts from two flows:

1. Ending a usage session (`/sessions/active/` → *Send STK*)
2. Recording a payment (`/add_payment/`)

Both flows share the same helper functions and callback endpoint. Follow the steps below to configure and test the integration.

---

## 1. Environment loading (`cyber/settings.py`)

`settings.py` calls `load_dotenv(os.path.join(BASE_DIR, '.env'))` where `BASE_DIR = Path(__file__).resolve().parent.parent`. That means the `.env` file must live at `cyber/.env` (project root, not next to `settings.py`). Populate it with the Daraja credentials the code expects:

```
# Django
SECRET_KEY=your-secret
DEBUG=True

# Daraja sandbox (or production)
MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=xxxxxxxxxxxxxxxxxxxx
MPESA_CONSUMER_SECRET=xxxxxxxxxxxxxxxxxxxx
MPESA_SHORTCODE=174379
MPESA_EXPRESS_SHORTCODE=174379
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
MPESA_CALLBACK_URL=https://<public-domain>/mpesa/callback/
```

**Important:** `MPESA_EXPRESS_SHORTCODE` is required by django-daraja even if it equals `MPESA_SHORTCODE`. `MPESA_CALLBACK_URL` must be an HTTPS URL reachable by Safaricom (e.g., ngrok tunnel for local dev).

After editing `.env`, restart the Django server so the variables load. If `MPESA_EXPRESS_SHORTCODE` or any other key is missing, django-daraja raises `MpesaConfigurationException` before the STK request goes out.

---

## 2. Callback routing (`cyberapp/urls.py` + `views.py`)

`cyberapp/urls.py` maps `path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback')`. The callback view lives in `cyberapp/views.py` and:

1. Parses the JSON body.
2. Finds a `UsageSession` or `Payment` whose `mpesa_checkout_request_id` matches `CheckoutRequestID`.
3. Marks the object as `paid`/`failed`, stores receipt numbers and phone numbers when available.
4. Returns `{'ResultCode': 0, 'ResultDesc': 'Accepted'}` so Safaricom treats the callback as acknowledged.

Every STK initiation builds the callback URL through `_resolve_callback_url()`; if the env var still contains the placeholder, it falls back to `request.build_absolute_uri(reverse('mpesa_callback'))`.

---

## 3. Exposing the callback URL (ngrok / hosting)

The project defines `path('mpesa/callback/', views.mpesa_callback, ...)`. Safaricom must POST to this route. For local testing:

1. Start the dev server: 
   `../.venv/bin/python manage.py runserver 0.0.0.0:8000`
2. Start a tunnel, e.g. `ngrok http 8000`.
3. Update `.env` and the Daraja portal to use `https://<ngrok-id>.ngrok.io/mpesa/callback/`.

Your tunnel must stay running while you test, otherwise Safaricom cannot reach the callback.

---

## 4. Session STK flow (views + JS)

* UI: `Active Sessions → End Session → Send STK`
* When a session ends, we store the final billable amount.
* Clicking **Send STK** prompts the operator for a phone number (defaulting to the student’s number).  
* The browser calls `/sessions/<id>/stk/` which invokes `MpesaClient.stk_push`.  
* On success, `UsageSession.payment_status` is set to `pending` with the `CheckoutRequestID`.
* When Safaricom calls back, `/mpesa/callback/` sets the session to `paid` or `failed` and stores the receipt.

---

## 5. Payment STK flow (`add_payment`)

* UI: `Record payment (/add_payment/)`
* The form allows entering Amount, Balance, Date, Student, plus an optional phone override.
* On submit, we send an STK push for the entered amount. The `Payment` row stores:
  - `mpesa_status` (`pending`, `paid`, `failed`)
  - `mpesa_checkout_request_id`
  - `mpesa_receipt_number`
  - `mpesa_phone_number`
* The payments list page shows the current STK status and receipt (if available).

---

## 6. Troubleshooting checklist

| Symptom | Fix |
|--------|-----|
| `MPESA_EXPRESS_SHORTCODE not found` | `.env` must live in `cyber/.env`; add `MPESA_EXPRESS_SHORTCODE` and restart server. |
| `Bad Request – Invalid CallBackURL` | Use a public HTTPS URL ending with `/mpesa/callback/`. Ngrok must be running. |
| STK push shows `Could not initiate STK push` | Check the server logs for the precise exception; usually invalid credentials or network issues. |
| Callback never marks status as paid | Verify Safaricom can reach your callback (check ngrok/hosting logs) and that `MPESA_CALLBACK_URL` matches the registered URL. |

---

With these steps complete, the STK push integration should work for both session billing and manual payments. If you modify the flow (e.g., adding other payment methods), update this document accordingly.

