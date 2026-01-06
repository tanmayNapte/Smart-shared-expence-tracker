💰 Smart Shared Expense Tracker (Debt Engine)

A Flask-based web application to manage shared expenses, balances, and settlements within groups.
Designed to keep expense tracking simple, transparent, and fair — without unnecessary complexity.

🚀 Features

🔐 User Authentication

Secure login system

Role-based access (Admin / User)

👥 Group Management

Create groups for trips, flats, or events

Add members to groups

View only groups you belong to

💸 Expense Tracking

Add expenses with payer and description

Automatically split expenses among group members

⚖️ Balance Calculation

See who owes money and who should get paid

Real-time balance updates per member

🔁 Suggested Settlements

Smart recommendations on who should pay whom

Minimizes number of transactions needed to settle balances

🧾 Settlement Records

Record settlements between members

View settlement history with timestamps

🎨 Clean UI

Card-based layout

Old-money inspired neutral color palette

Responsive and readable typography

🛠 Tech Stack

Backend: Python, Flask

Database: PostgreSQL (production), SQLite (local)

ORM: SQLAlchemy

Frontend: HTML, Jinja2, CSS

Authentication: Flask sessions

📂 Project Structure
Smart_Expence_tracker/
│
├── app.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── group.html
│   └── auth templates
│
├── static/
│   └── style.css
│
├── .gitignore
