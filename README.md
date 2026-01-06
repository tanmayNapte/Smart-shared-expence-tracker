# Smart Shared Expense Tracker (Debt Engine)

A Flask-based web application to manage **shared group expenses**, calculate **balances**, and generate **optimal settlement suggestions**.

---

## 🚀 Features

- User authentication (login / logout)
- Group-based expense tracking
- Automatic balance calculation
- Suggested settlements to minimize transactions
- Settlement history tracking
- Admin role for user creation
- Clean card-based UI

---

## 🛠 Tech Stack

- **Backend:** Python, Flask
- **ORM:** SQLAlchemy
- **Database:** PostgreSQL (production) / SQLite (development)
- **Frontend:** Jinja2, HTML, CSS
- **Auth:** Session-based authentication

---

## 📂 Project Structure


Smart_Expence_tracker/
│
├── app.py
├── requirements.txt
├── .gitignore
│
├── templates/
│ ├── base.html
│ ├── login.html
│ ├── dashboard.html
│ ├── create_group.html
│ ├── group.html
│ └── add_members.html
│
└── static/
└── style.css

