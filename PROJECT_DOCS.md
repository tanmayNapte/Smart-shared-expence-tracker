# Smart Shared Expense Tracker (Ledger) - Project Documentation

## 1. Project Overview
**Ledger** is a Flask-based web application designed to simplify shared expense tracking. It simulates a "Ledger" interface where groups of friends or roommates can track expenses, view balances, and settle debts. The application focuses on privacy, ease of use, and a clear "who owes whom" presentation.

## 2. Technical Stack
*   **Backend**: Python, Flask, SQLAlchemy (SQLite/PostgreSQL compatible).
*   **Frontend**: HTML5, jinja2 templates, raw CSS (no heavy frameworks), Vanilla JavaScript.
*   **Database**: Relational DB (Users, Groups, Expenses, Settlements).

## 3. Features & Functionality

### 3.1 Authentication & User Management
*   **Registration/Login**: Standard email/password flow.
*   **Profile**: Users can view their profile details.
*   **Admin Access**: Special role (`role="admin"`) that allows creating users and managing group members.

### 3.2 Groups
*   **Context**: All expenses happen within a "Group".
*   **Functionality**: Users can create multiples groups, view members, and rename/delete groups (permissions protected).
*   **Logic**: A group acts as a container for expenses and a boundary for calculations.

### 3.3 Expense Tracking
*   **Creation**: Users add expenses to a group, specifying the *Amount*, *Description*, and *Who Paid*.
*   **Splitting Implementation**: By default, **all expenses are split equally** among all group members at the moment of creation.
*   **Editing**: Expenses can be edited (Amount/Payer), which triggers a recalculation of splits.

### 3.4 Settlements
*   **Concept**: A "Settlement" is a direct payment from User A to User B to reduce debt.
*   **Impact**: Settlements reduce the "Net Balance" between two users in the ledger system.

### 3.5 Dashboard & Logic
*   **Net Position**: The dashboard features unique "You Owe" and "You Get" cards.
*   **Calculations**: The `ledger_service.py` aggregates all expenses a user has paid vs. splits they are responsible for, minus any settlements, to show a final net position per person.

## 4. Page-by-Page Analysis

| Page / Route | Description | Key Features |
| :--- | :--- | :--- |
| **Login / Register** | Auth pages | Simple, secure forms. |
| **Dashboard** (`/dashboard`) | Main landing page | • Summary cards (Total Balance)<br>• **People Balances**: Specific list of who owes you vs. who you owe.<br>• Recent Activity feed. |
| **My Groups** (`/groups`) | List view | Cards for each group a user belongs to. |
| **Group Detail** (`/groups/<id>`) | Deep dive into a group | • **Stats**: Total group spending.<br>• **Tabs**: Members, Expenses, Balances, Settlements.<br>• **Smart Suggestions**: "Refund X to Y" based on simplified debt. |
| **Create Expense** | Form page | Dropdown for Group and Payer. Link to create expenses. |
| **Activity Feed** (`/activity`) | History log | Chronological list of all actions (Created Group, Added Expense, Settled). |
| **User Profile** (`/profile`) | Settings | View user details. |
| **Admin Tools** | Hidden/protected pages | `create_user.html` and `add_members.html` (accessible only to users with `role='admin'`). |

## 5. Strengths & Weaknesses

### Strengths
1.  **Robust Ledger Logic**: The backend (`ledger_service.py`) correctly handles the complex math of "who owes whom" across multiple groups and transactions, providing a reliable "Net Position".
2.  **Clean Architecture**: The project follows a strict Service-Repository pattern (Routes -> Services -> Models), keeping `app.py` clean and logic testable.
3.  **Security**: Basic security permissions are enforced (e.g., cannot edit others' expenses, cannot view groups you aren't in).
4.  **UI Consistency**: The design uses a consistent "Ledger" theme with a sidebar, distinct typography (Inter/Playfair), and clear financial indicators (Green/Red for positive/negative balances).

### Weaknesses (Room for Improvement)
1.  **Rigid Splitting**: Currently, expenses are *automatically split equally* among all group members. There is no UI to support unequal splits (e.g. 60/40) or to exclude specific members from an expense.
2.  **Member Management Friction**: Adding members to an existing group is currently restricted to **Admins only**. Normal users cannot invite friends to their groups after creation, which limits usability.
3.  **Performance Scalability**: The balance calculation iterates through *all* past expenses dynamically. As data grows, this page load time will increase significantly without caching or database optimization.
4.  **Mobile Experience**: While responsive, the sidebar and tables might feel cramped on very small screens.
