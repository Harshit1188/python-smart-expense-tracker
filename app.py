
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
import sqlite3
from functools import wraps
from datetime import date, datetime, timedelta
from pathlib import Path
import calendar

app = Flask(__name__)

app.secret_key = "expense_tracker_secret_key"

# Keep the database in the same folder as app.py
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "expenses.db"

CATEGORIES = [
    "Shopping",
    "Education",
    "Travel",
    "Healthcare",
    "Entertainment",
    "Food",
    "Bills",
    "Other"
]


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def init_db():
    conn = get_db()

    # Existing expense records are preserved.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TEXT NOT NULL
        )
    """)

    # Create budget table if it does not exist.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# LOGIN REQUIRED DECORATOR
# ==========================================

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    if "user" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == "admin" and password == "admin123":

            session["user"] = username

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()

    # --------------------------------------
    # SELECTED MONTH
    # --------------------------------------

    current_month = date.today().strftime("%Y-%m")

    selected_month = request.args.get(
        "month",
        current_month
    )

    try:
        datetime.strptime(selected_month, "%Y-%m")
    except ValueError:
        selected_month = current_month

    # --------------------------------------
    # SEARCH AND FILTER VALUES
    # --------------------------------------

    search = request.args.get("q", "").strip()

    selected_category = request.args.get(
        "category",
        ""
    )

    start_date = request.args.get(
        "start_date",
        ""
    )

    end_date = request.args.get(
        "end_date",
        ""
    )

    # --------------------------------------
    # TOTAL ALL-TIME EXPENSES
    # --------------------------------------

    total = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """).fetchone()[0]

    total = float(total or 0)

    # --------------------------------------
    # SELECTED MONTH TOTAL
    # --------------------------------------

    monthly_total = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE substr(expense_date, 1, 7) = ?
    """, (selected_month,)).fetchone()[0]

    monthly_total = float(monthly_total or 0)

    # --------------------------------------
    # CATEGORY BREAKDOWN
    # --------------------------------------

    categories = conn.execute("""
        SELECT
            category,
            SUM(amount) AS total
        FROM expenses
        WHERE substr(expense_date, 1, 7) = ?
        GROUP BY category
        ORDER BY total DESC
    """, (selected_month,)).fetchall()

    # Highest spending category
    highest_category = (
        categories[0] if categories else None
    )

    category_names = [
        row["category"] for row in categories
    ]

    category_values = [
        float(row["total"] or 0)
        for row in categories
    ]

    # --------------------------------------
    # AVAILABLE CATEGORIES FOR FILTER
    # --------------------------------------

    available_categories = conn.execute("""
        SELECT DISTINCT category
        FROM expenses
        ORDER BY category
    """).fetchall()

    # --------------------------------------
    # MONTHLY BUDGET
    # --------------------------------------

    budget_row = conn.execute("""
        SELECT amount
        FROM budgets
        WHERE month = ?
    """, (selected_month,)).fetchone()

    budget = (
        float(budget_row["amount"])
        if budget_row else 0
    )

    remaining = budget - monthly_total

    budget_percentage = 0

    if budget > 0:
        budget_percentage = (
            monthly_total / budget
        ) * 100

    # --------------------------------------
    # MONTHLY SPENDING TREND
    # LAST SIX MONTHS
    # --------------------------------------

    monthly_data = conn.execute("""
        SELECT
            substr(expense_date, 1, 7) AS month,
            SUM(amount) AS total
        FROM expenses
        WHERE
            length(expense_date) = 10
            AND substr(expense_date, 1, 7)
                BETWEEN ? AND ?
        GROUP BY substr(expense_date, 1, 7)
        ORDER BY month ASC
    """, (
        (
            date.today().replace(day=1)
            - timedelta(days=150)
        ).strftime("%Y-%m"),
        current_month
    )).fetchall()

    # Convert database results into Chart.js data.
    monthly_labels = [
        row["month"] for row in monthly_data
    ]

    monthly_values = [
        float(row["total"] or 0)
        for row in monthly_data
    ]

    # --------------------------------------
    # EXPENSE SEARCH AND FILTER
    # --------------------------------------

    query = """
        SELECT *
        FROM expenses
        WHERE 1 = 1
    """

    params = []

    # Selected month filter
    query += " AND substr(expense_date, 1, 7) = ?"
    params.append(selected_month)

    # Search by expense title
    if search:
        query += " AND title LIKE ?"
        params.append("%" + search + "%")

    # Category filter
    if selected_category:
        query += " AND category = ?"
        params.append(selected_category)

    # Starting date filter
    if start_date:
        query += " AND expense_date >= ?"
        params.append(start_date)

    # Ending date filter
    if end_date:
        query += " AND expense_date <= ?"
        params.append(end_date)

    query += """
        ORDER BY expense_date DESC, id DESC
    """

    expenses = conn.execute(
        query,
        params
    ).fetchall()

    # --------------------------------------
    # SMART SPENDING INSIGHTS
    # --------------------------------------

    insights = []

    if monthly_total == 0:

        insights.append(
            "No expenses recorded for this month. "
            "Add your expenses to start tracking."
        )

    else:

        if highest_category:

            insights.append(
                "Your highest spending category is "
                + highest_category["category"]
                + " with ₹"
                + format(float(highest_category["total"]), ".2f")
                + " spent."
            )

        if budget > 0:

            if monthly_total > budget:

                insights.append(
                    "You have exceeded your monthly budget by ₹"
                    + format(monthly_total - budget, ".2f")
                    + ". Try reducing your spending."
                )

            else:

                insights.append(
                    "You have ₹"
                    + format(remaining, ".2f")
                    + " remaining in your monthly budget."
                )

        else:

            insights.append(
                "Set a monthly budget to manage your spending better."
            )

        if len(categories) > 1:

            insights.append(
                "You have expenses across "
                + str(len(categories))
                + " different categories."
            )

    # --------------------------------------
    # CLOSE DATABASE
    # --------------------------------------

    conn.close()

    # --------------------------------------
    # SEND DATA TO DASHBOARD
    # --------------------------------------

    return render_template(
        "dashboard.html",

        total=total,
        monthly_total=monthly_total,

        categories=categories,
        highest_category=highest_category,

        expenses=expenses,
        available_categories=available_categories,

        selected_month=selected_month,
        selected_category=selected_category,

        search=search,
        start_date=start_date,
        end_date=end_date,

        budget=budget,
        remaining=remaining,
        budget_percentage=budget_percentage,

        insights=insights,

        category_names=category_names,
        category_values=category_values,

        monthly_labels=monthly_labels,
        monthly_values=monthly_values
    )


# ==========================================
# ADD EXPENSE
# ==========================================

@app.route("/add", methods=["POST"])
@login_required
def add():

    title = request.form.get(
        "title", ""
    ).strip()

    category = request.form.get(
        "category", ""
    ).strip()

    amount = request.form.get(
        "amount", ""
    ).strip()

    expense_date = request.form.get(
        "expense_date", ""
    ).strip()

    # Validate amount
    try:

        amount = float(amount)

        if amount <= 0:
            raise ValueError

    except ValueError:

        return "Enter a valid amount.", 400

    # Validate required fields
    if not title or not category or not expense_date:
        return "Please fill in all fields.", 400

    # Validate date
    try:
        datetime.strptime(expense_date, "%Y-%m-%d")
    except ValueError:
        return "Enter a valid expense date.", 400

    conn = get_db()

    conn.execute("""
        INSERT INTO expenses (
            title,
            category,
            amount,
            expense_date
        )
        VALUES (?, ?, ?, ?)
    """, (
        title,
        category,
        amount,
        expense_date
    ))

    conn.commit()
    conn.close()

    return redirect(url_for(
        "dashboard",
        month=expense_date[:7]
    ))


# ==========================================
# SET MONTHLY BUDGET
# ==========================================

@app.route("/budget", methods=["POST"])
@login_required
def set_budget():

    month = request.form.get(
        "month",
        date.today().strftime("%Y-%m")
    )

    amount = request.form.get(
        "budget",
        ""
    ).strip()

    try:

        datetime.strptime(month, "%Y-%m")

        amount = float(amount)

        if amount <= 0:
            raise ValueError

    except ValueError:

        return "Enter a valid month and budget amount.", 400

    conn = get_db()

    conn.execute("""
        INSERT INTO budgets (month, amount)
        VALUES (?, ?)
        ON CONFLICT(month)
        DO UPDATE SET amount = excluded.amount
    """, (month, amount))

    conn.commit()
    conn.close()

    return redirect(url_for(
        "dashboard",
        month=month
    ))


# ==========================================
# EDIT EXPENSE
# ==========================================

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):

    conn = get_db()

    expense = conn.execute("""
        SELECT *
        FROM expenses
        WHERE id = ?
    """, (id,)).fetchone()

    if expense is None:

        conn.close()

        return "Expense not found.", 404

    if request.method == "POST":

        title = request.form.get(
            "title", ""
        ).strip()

        category = request.form.get(
            "category", ""
        ).strip()

        amount = request.form.get(
            "amount", ""
        ).strip()

        expense_date = request.form.get(
            "expense_date", ""
        ).strip()

        try:

            amount = float(amount)

            if amount <= 0:
                raise ValueError

            datetime.strptime(
                expense_date,
                "%Y-%m-%d"
            )

        except ValueError:

            conn.close()

            return "Enter valid expense details.", 400

        if not title or not category:
            conn.close()
            return "Please fill in all fields.", 400

        conn.execute("""
            UPDATE expenses
            SET
                title = ?,
                category = ?,
                amount = ?,
                expense_date = ?
            WHERE id = ?
        """, (
            title,
            category,
            amount,
            expense_date,
            id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for(
            "dashboard",
            month=expense_date[:7]
        ))

    conn.close()

    return render_template(
        "edit_expense.html",
        expense=expense,
        categories=CATEGORIES
    )


# ==========================================
# DELETE EXPENSE
# ==========================================

@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):

    conn = get_db()

    conn.execute("""
        DELETE FROM expenses
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)
