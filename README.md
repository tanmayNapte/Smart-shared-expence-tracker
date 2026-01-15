# Smart Expense Tracker

Smart Expense Tracker is a Flask-based web application designed to simplify the process of tracking shared expenses among friends, family, or roommates. It allows users to create groups, log expenses, split costs accurately, and settle debts with ease.

## 🚀 Features

-   **User Authentication**: Secure sign-up and login functionality.
-   **Dashboard**: Overview of your financial status, including amounts you owe and are owed.
-   **Group Management**: Create groups and invite members to share expenses.
-   **Expense Tracking**: Add expenses with detailed descriptions and amounts.
-   **Smart Splitting**: Automatically handles expense splits among group members.
-   **Settlements**: Record and track payments to settle debts between users.
-   **Activity Feed**: View recent group activities and transactions.

## 🛠️ Tech Stack

-   **Backend Framework**: Python (Flask)
-   **Database**: SQLAlchemy (ORM)
-   **Frontend**: HTML5, CSS3, Jinja2 Templates
-   **Authentication**: Flask-Session / Custom Auth (based on `routes/auth.py`)

## 📂 Directory Structure

```plaintext
Smart_Expence_tracker/
├── app.py                  # Main application entry point
├── config.py               # Configuration settings
├── models.py               # Database models (User, Group, Expense, etc.)
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── routes/                 # Request handlers (Blueprints)
│   ├── auth.py             # Authentication routes
│   ├── expenses.py         # Expense management routes
│   ├── groups.py           # Group management routes
│   ├── settlements.py      # Settlement routes
│   └── users.py            # User profile routes
├── services/               # Business logic layer
├── templates/              # HTML templates
└── static/                 # Static assets (CSS, images)
```

## ⚡ Getting Started

### Prerequisites

-   Python 3.8 or higher
-   pip (Python package installer)

### Installation

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd Smart_Expence_tracker
    ```

2.  **Create a virtual environment (Optional but Recommended)**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Environment Variables**
    Create a `.env` file in the root directory if one is not provided, and ensure you have the necessary configurations (like `SECRET_KEY`, `DATABASE_URL`).

5.  **Run the Application**
    ```bash
    python app.py
    ```
    The application will start on `http://127.0.0.1:8001` (or the port specified in `app.py`).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 Owner

Tanmay Napte @2026

