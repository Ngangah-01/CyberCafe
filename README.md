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
# CyberCafe Management System

A full-featured Django web application designed for managing a cyber café.  
It provides real-time session tracking, automated billing, admin authentication, STK (M-Pesa) payment workflow, and an intuitive dashboard for managing student usage sessions.

---

## 🚀 Features

### ✅ 1. Admin Authentication
- Secure login system  
- Animated user profile dropdown  
- Logout functionality  
- Access protection using Django authentication middleware  

### ✅ 2. Student Management
- Register students (with ID, names, etc.)  
- View all registered students  
- View students with active sessions  

### ✅ 3. Session Tracking
- Start new sessions  
- Live real-time timer per user  
- Automatically calculates:  
  - Time spent (`HH:MM:SS`)  
  - Billing cost (KSH 100/hour, prorated)  
- End session with instant UI update (AJAX)  
- Toast notifications for completed sessions  

### ✅ 4. Billing System
- Billing is calculated dynamically:  
  `amount = hours_used × 100`  
- Final amount displayed when session ends  
- Ready for M-Pesa STK integration  

### ✅ 5. STK Push (M-Pesa Integration Ready)
- STK button automatically enables when session ends  
- Placeholder function in JS ready for real Daraja API call  

### ✅ 6. Clean Responsive UI
- Modern glassmorphic login page  
- Professional dashboard  
- Animated icons and dropdown  
- Clean table layouts for sessions & students  

### ✅ 7. AJAX-Powered Actions
- Ending a session happens instantly without page reload  
- Smooth front-end updates  
- JSON-based communication for reliability

## ⚙️ Installation & Setup (Local Development)

### 🔽 1. Clone the repository
git clone https://github.com/Ngangah-01/CyberCafe.git
cd CyberCafe

### 🛠 2. Create & activate a virtual environment
python -m venv env
env\Scripts\activate

### 📦 3. Install required dependencies
pip install -r requirements.txt

### 🗄️ 4. Apply database migrations
python manage.py migrate

### 👑 5. Create admin user
python manage.py createsuperuser

### ▶️ 6. Run the local server
python manage.py runserver

---

## 🏗️ Tech Stack

| Area        | Technology                        |
|-------------|-----------------------------------|
| Backend     | Django 5+                         |
| Database    | PostgreSQL (production), SQLite   |
| Frontend    | HTML5, CSS3, JavaScript           |
| AJAX        | Fetch API                         |
| Deployment  | Render.com                        |
| Payment     | Daraja (M-Pesa STK Push)          |
| Environment | Python venv                       |

---

## 📁 Project Structure

```text
CyberCafe/
├── cyber/                # Main Django project
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── templates/
│       ├── login.html
│       ├── dashboard.html
│       ├── active_sessions.html
│       └── ...
│
├── app/                  # Core application
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── static/
│       ├── styles/
│       │   └── styles.css
│       └── js/
│           └── scripts.js
│
├── env/                  # Virtual environment (ignored in Git)
├── manage.py
├── requirements.txt
├── runtime.txt
└── README.md




