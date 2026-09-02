import sqlite3
from pathlib import Path
from datetime import datetime


import os
import sqlite3

from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(
    os.getenv(
        "DATA_DIR",
        str(BASE_DIR)
    )
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

DB_FILE = DATA_DIR / "finance.db"


def get_connection():
    return sqlite3.connect(DB_FILE)


def init_database():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS savings_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        target_amount REAL NOT NULL,
        saved_amount REAL NOT NULL DEFAULT 0,
        currency TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(name, currency)
    )
""")


    connection.commit()
    connection.close()


def add_expense(
    amount,
    category,
    description="",
    currency="MDL"
):

    amount, error = validate_amount(amount)

    if error:
        return error

    category = category.strip().lower()
    currency = currency.upper()

    connection = get_connection()
    cursor = connection.cursor()

    

    cursor.execute("""
        INSERT INTO transactions (
            type,
            amount,
            currency,
            category,
            description,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "expense",
        amount,
        currency,
        category,
        description,
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()

    return (
        f"Расход сохранён: "
        f"{amount} {currency}, "
        f"категория: {category}."
    )


def add_income(
    amount,
    category,
    description="",
    currency="MDL"
):
    amount, error = validate_amount(amount)

    if error:
        return error

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO transactions (
            type,
            amount,
            currency,
            category,
            description,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "income",
        amount,
        currency,
        category,
        description,
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()

    return (
        f"Доход сохранён: "
        f"{amount} {currency}, "
        f"категория: {category}."
    )
def get_today_summary():
    connection = get_connection()
    cursor = connection.cursor()

    today = datetime.now().date().isoformat()

    cursor.execute("""
        SELECT type, amount, currency, category
        FROM transactions
        WHERE DATE(created_at) = ?
    """, (today,))

    rows = cursor.fetchall()

    connection.close()

    if not rows:
        return "Сегодня финансовых операций пока нет."

    total_income = 0
    total_expense = 0

    expenses_by_category = {}
    incomes_by_category = {}

    for transaction_type, amount, currency, category in rows:

        if transaction_type == "expense":
            total_expense += amount

            expenses_by_category[category] = (
                expenses_by_category.get(category, 0)
                + amount
            )

        elif transaction_type == "income":
            total_income += amount

            incomes_by_category[category] = (
                incomes_by_category.get(category, 0)
                + amount
            )

    balance = total_income - total_expense

    result = (
        f"Сегодня:\n"
        f"Доходы: {total_income} MDL\n"
        f"Расходы: {total_expense} MDL\n"
        f"Разница: {balance} MDL\n"
    )

    if expenses_by_category:
        result += "\nРасходы по категориям:\n"

        for category, amount in expenses_by_category.items():
            result += f"- {category}: {amount} MDL\n"

    if incomes_by_category:
        result += "\nДоходы по категориям:\n"

        for category, amount in incomes_by_category.items():
            result += f"- {category}: {amount} MDL\n"

    return result
def get_recent_transactions(limit=10):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            type,
            amount,
            currency,
            category,
            description,
            created_at
        FROM transactions
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    connection.close()

    if not rows:
        return "Финансовых операций пока нет."

    result = "Последние операции:\n"

    for row in rows:
        (
            transaction_id,
            transaction_type,
            amount,
            currency,
            category,
            description,
            created_at
        ) = row

        result += (
            f"ID {transaction_id} | "
            f"{transaction_type} | "
            f"{amount} {currency} | "
            f"{category}"
        )

        if description:
            result += f" | {description}"

        result += "\n"

    return result
def delete_transaction(transaction_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            type,
            amount,
            currency,
            category
        FROM transactions
        WHERE id = ?
    """, (transaction_id,))

    transaction = cursor.fetchone()

    if transaction is None:
        connection.close()
        return f"Операция с ID {transaction_id} не найдена."

    cursor.execute("""
        DELETE FROM transactions
        WHERE id = ?
    """, (transaction_id,))

    connection.commit()
    connection.close()

    (
        transaction_id,
        transaction_type,
        amount,
        currency,
        category
    ) = transaction

    return (
        f"Операция удалена: "
        f"ID {transaction_id}, "
        f"{transaction_type}, "
        f"{amount} {currency}, "
        f"{category}."
    )
def update_transaction(
    transaction_id,
    amount=None,
    category=None,
    description=None,
    currency=None
    
):
    if amount is not None:
        amount, error = validate_amount(amount)

        if error:
            return error
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            type,
            amount,
            currency,
            category,
            description
        FROM transactions
        WHERE id = ?
    """, (transaction_id,))

    transaction = cursor.fetchone()

    if transaction is None:
        connection.close()
        return f"Операция с ID {transaction_id} не найдена."

    (
        transaction_id,
        transaction_type,
        old_amount,
        old_currency,
        old_category,
        old_description
    ) = transaction

    new_amount = (
        amount
        if amount is not None
        else old_amount
    )

    new_category = (
        category
        if category is not None
        else old_category
    )

    new_description = (
        description
        if description is not None
        else old_description
    )

    new_currency = (
        currency
        if currency is not None
        else old_currency
    )

    cursor.execute("""
        UPDATE transactions
        SET
            amount = ?,
            currency = ?,
            category = ?,
            description = ?
        WHERE id = ?
    """, (
        new_amount,
        new_currency,
        new_category,
        new_description,
        transaction_id
    ))

    connection.commit()
    connection.close()

    return (
        f"Операция ID {transaction_id} обновлена: "
        f"{new_amount} {new_currency}, "
        f"категория: {new_category}."
    )
def get_month_summary(
    year=None,
    month=None,
    currency="MDL"
):
    now = datetime.now()

    if year is None:
        year = now.year

    if month is None:
        month = now.month

    connection = get_connection()
    cursor = connection.cursor()

    month_string = f"{year}-{month:02d}"

    cursor.execute("""
        SELECT
            type,
            amount,
            category
        FROM transactions
        WHERE substr(created_at, 1, 7) = ?
        AND currency = ?
    """, (
        month_string,
        currency
    ))

    rows = cursor.fetchall()

    connection.close()

    if not rows:
        return (
            f"За {month:02d}.{year} "
            f"операций в {currency} нет."
        )

    total_income = 0
    total_expense = 0

    expenses_by_category = {}
    incomes_by_category = {}

    for transaction_type, amount, category in rows:

        if transaction_type == "expense":

            total_expense += amount

            expenses_by_category[category] = (
                expenses_by_category.get(
                    category,
                    0
                )
                + amount
            )

        elif transaction_type == "income":

            total_income += amount

            incomes_by_category[category] = (
                incomes_by_category.get(
                    category,
                    0
                )
                + amount
            )

    balance = total_income - total_expense

    result = (
        f"Финансовая сводка за "
        f"{month:02d}.{year}:\n"
        f"Доходы: {total_income:.2f} {currency}\n"
        f"Расходы: {total_expense:.2f} {currency}\n"
        f"Разница: {balance:.2f} {currency}\n"
    )

    if expenses_by_category:

        result += "\nРасходы по категориям:\n"

        sorted_expenses = sorted(
            expenses_by_category.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for category, amount in sorted_expenses:

            result += (
                f"- {category}: "
                f"{amount:.2f} {currency}\n"
            )

    if incomes_by_category:

        result += "\nДоходы по категориям:\n"

        sorted_incomes = sorted(
            incomes_by_category.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for category, amount in sorted_incomes:

            result += (
                f"- {category}: "
                f"{amount:.2f} {currency}\n"
            )

    return result
def compare_months(
    month1=None,
    year1=None,
    month2=None,
    year2=None,
    currency="MDL"
):
    now = datetime.now()

    # Первый период — текущий месяц,
    # если пользователь ничего не указал
    if month1 is None:
        month1 = now.month

    if year1 is None:
        year1 = now.year


    # Второй период — предыдущий месяц,
    # если пользователь ничего не указал
    if month2 is None:

        if month1 == 1:
            month2 = 12
            year2 = year1 - 1
        else:
            month2 = month1 - 1

    if year2 is None:
        year2 = year1


    def get_totals(year, month):

        connection = get_connection()
        cursor = connection.cursor()

        month_string = f"{year}-{month:02d}"

        cursor.execute("""
            SELECT
                type,
                SUM(amount)
            FROM transactions
            WHERE substr(created_at, 1, 7) = ?
            AND currency = ?
            GROUP BY type
        """, (
            month_string,
            currency
        ))

        rows = cursor.fetchall()

        connection.close()

        income = 0
        expense = 0

        for transaction_type, total in rows:

            if transaction_type == "income":
                income = total or 0

            elif transaction_type == "expense":
                expense = total or 0

        return {
            "income": income,
            "expense": expense,
            "balance": income - expense
        }


    first = get_totals(
        year1,
        month1
    )

    second = get_totals(
        year2,
        month2
    )


    # Изменение расходов в процентах
    if second["expense"] > 0:

        expense_change = (
            (
                first["expense"]
                - second["expense"]
            )
            / second["expense"]
            * 100
        )

        expense_change_text = (
            f"{expense_change:+.1f}%"
        )

    else:

        expense_change_text = (
            "невозможно рассчитать"
        )


    # Изменение доходов в процентах
    if second["income"] > 0:

        income_change = (
            (
                first["income"]
                - second["income"]
            )
            / second["income"]
            * 100
        )

        income_change_text = (
            f"{income_change:+.1f}%"
        )

    else:

        income_change_text = (
            "невозможно рассчитать"
        )


    result = (
        f"Сравнение периодов:\n\n"

        f"{month1:02d}.{year1}:\n"
        f"Доходы: {first['income']:.2f} {currency}\n"
        f"Расходы: {first['expense']:.2f} {currency}\n"
        f"Разница: {first['balance']:.2f} {currency}\n\n"

        f"{month2:02d}.{year2}:\n"
        f"Доходы: {second['income']:.2f} {currency}\n"
        f"Расходы: {second['expense']:.2f} {currency}\n"
        f"Разница: {second['balance']:.2f} {currency}\n\n"

        f"Изменение расходов: "
        f"{expense_change_text}\n"

        f"Изменение доходов: "
        f"{income_change_text}"
    )

    return result

def get_savings_rate(
    year=None,
    month=None,
    currency="MDL"
):
    now = datetime.now()

    if year is None:
        year = now.year

    if month is None:
        month = now.month

    connection = get_connection()
    cursor = connection.cursor()

    month_string = f"{year}-{month:02d}"

    cursor.execute("""
        SELECT
            type,
            SUM(amount)
        FROM transactions
        WHERE substr(created_at, 1, 7) = ?
        AND currency = ?
        GROUP BY type
    """, (
        month_string,
        currency
    ))

    rows = cursor.fetchall()

    connection.close()

    total_income = 0
    total_expense = 0

    for transaction_type, total in rows:

        if transaction_type == "income":
            total_income = total or 0

        elif transaction_type == "expense":
            total_expense = total or 0

    savings = total_income - total_expense

    if total_income <= 0:
        return (
            f"За {month:02d}.{year} "
            f"доходов в {currency} нет, "
            f"поэтому процент сбережений "
            f"рассчитать нельзя."
        )

    savings_rate = (
        savings / total_income
    ) * 100

    return (
        f"Сбережения за {month:02d}.{year}:\n"
        f"Доходы: {total_income:.2f} {currency}\n"
        f"Расходы: {total_expense:.2f} {currency}\n"
        f"Осталось: {savings:.2f} {currency}\n"
        f"Процент сбережений: {savings_rate:.1f}%"
    )
def get_category_breakdown(
    year=None,
    month=None,
    currency="MDL"
):
    now = datetime.now()

    if year is None:
        year = now.year

    if month is None:
        month = now.month

    month_string = f"{year}-{month:02d}"

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            category,
            SUM(amount)
        FROM transactions
        WHERE type = 'expense'
        AND substr(created_at, 1, 7) = ?
        AND currency = ?
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (
        month_string,
        currency
    ))

    rows = cursor.fetchall()

    connection.close()

    if not rows:
        return (
            f"За {month:02d}.{year} "
            f"расходов в {currency} нет."
        )

    total_expense = sum(
        amount
        for category, amount in rows
    )

    result = (
        f"Расходы по категориям "
        f"за {month:02d}.{year}:\n"
    )

    for category, amount in rows:

        percentage = (
            amount / total_expense
        ) * 100

        result += (
            f"- {category}: "
            f"{amount:.2f} {currency} "
            f"({percentage:.1f}%)\n"
        )

    top_category, top_amount = rows[0]

    result += (
        f"\nСамая крупная категория: "
        f"{top_category} — "
        f"{top_amount:.2f} {currency}."
    )

    return result
def set_budget(
    category,
    amount,
    currency="MDL"
):
    if amount <= 0:
        return "Бюджет должен быть больше нуля."

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO budgets (
            category,
            amount,
            currency,
            updated_at
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(category, currency)
        DO UPDATE SET
            amount = excluded.amount,
            updated_at = excluded.updated_at
    """, (
        category,
        amount,
        currency,
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()

    return (
        f"Бюджет установлен: "
        f"{category} — "
        f"{amount:.2f} {currency}."
    )
def get_budget_status(
    category=None,
    year=None,
    month=None,
    currency="MDL"
):
    now = datetime.now()

    if year is None:
        year = now.year

    if month is None:
        month = now.month

    month_string = f"{year}-{month:02d}"

    connection = get_connection()
    cursor = connection.cursor()

    if category:

        cursor.execute("""
            SELECT category, amount
            FROM budgets
            WHERE category = ?
            AND currency = ?
        """, (
            category,
            currency
        ))

    else:

        cursor.execute("""
            SELECT category, amount
            FROM budgets
            WHERE currency = ?
            ORDER BY category
        """, (
            currency,
        ))

    budgets = cursor.fetchall()

    if not budgets:
        connection.close()
        return "Подходящих бюджетов пока нет."

    result = (
        f"Бюджеты за {month:02d}.{year}:\n"
    )

    for budget_category, budget_amount in budgets:

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE type = 'expense'
            AND category = ?
            AND currency = ?
            AND substr(created_at, 1, 7) = ?
        """, (
            budget_category,
            currency,
            month_string
        ))

        spent = cursor.fetchone()[0]

        remaining = (
            budget_amount - spent
        )

        percentage = (
            spent / budget_amount * 100
        )

        result += (
            f"\n{budget_category}:\n"
            f"Бюджет: {budget_amount:.2f} {currency}\n"
            f"Потрачено: {spent:.2f} {currency}\n"
            f"Осталось: {remaining:.2f} {currency}\n"
            f"Использовано: {percentage:.1f}%\n"
        )

    connection.close()

    return result
def create_savings_goal(
    name,
    target_amount,
    currency="MDL"
):
    if target_amount <= 0:
        return "Сумма цели должна быть больше нуля."

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM savings_goals
        WHERE name = ?
        AND currency = ?
    """, (
        name,
        currency
    ))

    existing_goal = cursor.fetchone()

    if existing_goal:
        connection.close()

        return (
            f"Цель «{name}» в {currency} "
            f"уже существует."
        )

    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO savings_goals (
            name,
            target_amount,
            saved_amount,
            currency,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        target_amount,
        0,
        currency,
        now,
        now
    ))

    connection.commit()
    connection.close()

    return (
        f"Цель создана: «{name}» — "
        f"{target_amount:.2f} {currency}."
    )


def add_goal_progress(
    name,
    amount,
    currency="MDL"
):
    if amount <= 0:
        return "Добавляемая сумма должна быть больше нуля."

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            target_amount,
            saved_amount
        FROM savings_goals
        WHERE name = ?
        AND currency = ?
    """, (
        name,
        currency
    ))

    goal = cursor.fetchone()

    if goal is None:
        connection.close()

        return (
            f"Цель «{name}» "
            f"в {currency} не найдена."
        )

    goal_id, target_amount, saved_amount = goal

    new_saved_amount = saved_amount + amount

    cursor.execute("""
        UPDATE savings_goals
        SET
            saved_amount = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        new_saved_amount,
        datetime.now().isoformat(),
        goal_id
    ))

    connection.commit()
    connection.close()

    progress = (
        new_saved_amount / target_amount
    ) * 100

    remaining = max(
        target_amount - new_saved_amount,
        0
    )

    return (
        f"Цель «{name}» обновлена:\n"
        f"Накоплено: {new_saved_amount:.2f} {currency}\n"
        f"Цель: {target_amount:.2f} {currency}\n"
        f"Осталось: {remaining:.2f} {currency}\n"
        f"Прогресс: {progress:.1f}%"
    )


def get_savings_goals(
    name=None,
    currency="MDL"
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            target_amount,
            saved_amount
        FROM savings_goals
        WHERE currency = ?
        ORDER BY id DESC
    """, (
        currency,
    ))

    rows = cursor.fetchall()

    connection.close()

    if name is not None:

        rows = [
            row
            for row in rows
            if row[1].casefold() == name.casefold()
        ]

    if not rows:
        return "Подходящих финансовых целей нет."

    result = "Финансовые цели:\n"

    for (
        goal_id,
        goal_name,
        target_amount,
        saved_amount
    ) in rows:

        progress = (
            saved_amount / target_amount
        ) * 100

        remaining = max(
            target_amount - saved_amount,
            0
        )

        result += (
            f"\nID {goal_id} | {goal_name}\n"
            f"Цель: {target_amount:.2f} {currency}\n"
            f"Накоплено: {saved_amount:.2f} {currency}\n"
            f"Осталось: {remaining:.2f} {currency}\n"
            f"Прогресс: {progress:.1f}%\n"
        )

    return result
def get_financial_insights(
    year=None,
    month=None,
    currency="MDL"
):
    now = datetime.now()

    if year is None:
        year = now.year

    if month is None:
        month = now.month

    month_string = f"{year}-{month:02d}"

    connection = get_connection()
    cursor = connection.cursor()


    # -------------------------
    # ДОХОДЫ И РАСХОДЫ
    # -------------------------

    cursor.execute("""
        SELECT
            type,
            SUM(amount)
        FROM transactions
        WHERE substr(created_at, 1, 7) = ?
        AND currency = ?
        GROUP BY type
    """, (
        month_string,
        currency
    ))

    rows = cursor.fetchall()

    total_income = 0
    total_expense = 0

    for transaction_type, total in rows:

        if transaction_type == "income":
            total_income = total or 0

        elif transaction_type == "expense":
            total_expense = total or 0


    # -------------------------
    # КАТЕГОРИИ
    # -------------------------

    cursor.execute("""
        SELECT
            category,
            SUM(amount)
        FROM transactions
        WHERE type = 'expense'
        AND substr(created_at, 1, 7) = ?
        AND currency = ?
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (
        month_string,
        currency
    ))

    categories = cursor.fetchall()


    # -------------------------
    # БЮДЖЕТЫ
    # -------------------------

    cursor.execute("""
        SELECT
            category,
            amount
        FROM budgets
        WHERE currency = ?
    """, (
        currency,
    ))

    budgets = cursor.fetchall()


    # -------------------------
    # ЦЕЛИ
    # -------------------------

    cursor.execute("""
        SELECT
            name,
            target_amount,
            saved_amount
        FROM savings_goals
        WHERE currency = ?
    """, (
        currency,
    ))

    goals = cursor.fetchall()

    connection.close()


    balance = (
        total_income - total_expense
    )


    if total_income > 0:

        savings_rate = (
            balance / total_income
        ) * 100

        savings_text = (
            f"{savings_rate:.1f}%"
        )

    else:

        savings_text = (
            "нельзя рассчитать"
        )


    result = (
        f"Финансовые данные за "
        f"{month:02d}.{year}:\n\n"
        f"Доходы: {total_income:.2f} {currency}\n"
        f"Расходы: {total_expense:.2f} {currency}\n"
        f"Разница: {balance:.2f} {currency}\n"
        f"Процент сбережений: {savings_text}\n"
    )


    if categories:

        result += "\nКатегории расходов:\n"

        for category, amount in categories:

            percentage = (
                amount / total_expense * 100
                if total_expense > 0
                else 0
            )

            result += (
                f"- {category}: "
                f"{amount:.2f} {currency} "
                f"({percentage:.1f}%)\n"
            )


    if budgets:

        result += "\nБюджеты:\n"

        category_spending = dict(
            categories
        )

        for category, budget_amount in budgets:

            spent = category_spending.get(
                category,
                0
            )

            percentage = (
                spent / budget_amount * 100
                if budget_amount > 0
                else 0
            )

            result += (
                f"- {category}: "
                f"{spent:.2f} / "
                f"{budget_amount:.2f} {currency} "
                f"({percentage:.1f}%)\n"
            )


    if goals:

        result += "\nФинансовые цели:\n"

        for (
            name,
            target_amount,
            saved_amount
        ) in goals:

            progress = (
                saved_amount
                / target_amount
                * 100
                if target_amount > 0
                else 0
            )

            result += (
                f"- {name}: "
                f"{saved_amount:.2f} / "
                f"{target_amount:.2f} {currency} "
                f"({progress:.1f}%)\n"
            )


    return result

def validate_amount(amount):

    try:
        amount = float(amount)

    except (TypeError, ValueError):
        return None, "Сумма должна быть числом."

    if amount <= 0:
        return None, "Сумма должна быть больше нуля."

    return amount, None