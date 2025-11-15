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




