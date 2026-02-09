from fastmcp import FastMCP
import os
import sqlite3
import json
import csv
from datetime import datetime
from typing import Optional, Dict, List, Any
from io import StringIO

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("ExpenseTracker")

# Helper Functions
def load_categories() -> Dict[str, List[str]]:
    """Load and return categories from JSON file."""
    try:
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {}

def validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def validate_amount(amount: float) -> bool:
    """Validate amount is positive."""
    try:
        return float(amount) > 0
    except (ValueError, TypeError):
        return False

def validate_category(category: str, subcategory: str = "") -> Dict[str, Any]:
    """Validate category and subcategory exist."""
    categories = load_categories()
    
    if category not in categories:
        return {
            "valid": False,
            "error": f"Invalid category '{category}'. Available: {', '.join(categories.keys())}"
        }
    
    if subcategory and subcategory not in categories[category]:
        return {
            "valid": False,
            "error": f"Invalid subcategory '{subcategory}' for category '{category}'. Available: {', '.join(categories[category])}"
        }
    
    return {"valid": True}

def init_db():
    """Initialize database with expenses, budgets, and recurring expenses tables."""
    with sqlite3.connect(DB_PATH) as c:
        # Expenses table
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Budgets table
        c.execute("""
            CREATE TABLE IF NOT EXISTS budgets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                monthly_limit REAL NOT NULL,
                alert_threshold REAL DEFAULT 0.8,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Recurring expenses table
        c.execute("""
            CREATE TABLE IF NOT EXISTS recurring_expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT '',
                frequency TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                last_applied TEXT,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        c.commit()

init_db()

@mcp.tool()
def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    """Add a new expense entry to the database.
    
    Args:
        date: Date in YYYY-MM-DD format
        amount: Expense amount (must be positive)
        category: Expense category
        subcategory: Optional subcategory
        note: Optional note/description
    
    Returns:
        Success status with expense ID or error message, includes budget alert if threshold reached
    """
    try:
        # Validate inputs
        if not validate_date(date):
            return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
        
        if not validate_amount(amount):
            return {"status": "error", "message": "Amount must be a positive number"}
        
        cat_validation = validate_category(category, subcategory)
        if not cat_validation["valid"]:
            return {"status": "error", "message": cat_validation["error"]}
        
        # Insert expense
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, float(amount), category, subcategory, note)
            )
            expense_id = cur.lastrowid
            c.commit()
            
            # Check budget status for this category
            year_month = date[:7]  # Extract YYYY-MM from date
            budget_alert = None
            
            # Get budget for this category if it exists
            cur = c.execute(
                "SELECT monthly_limit, alert_threshold FROM budgets WHERE category = ?",
                (category,)
            )
            budget_row = cur.fetchone()
            
            if budget_row:
                limit, threshold = budget_row
                
                # Calculate month boundaries
                start_date = f"{year_month}-01"
                if year_month.endswith("02"):
                    year = int(year_month[:4])
                    last_day = "29" if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else "28"
                elif year_month.endswith(("04", "06", "09", "11")):
                    last_day = "30"
                else:
                    last_day = "31"
                end_date = f"{year_month}-{last_day}"
                
                # Get total spending for this category in the month
                cur = c.execute("""
                    SELECT COALESCE(SUM(amount), 0) as spent
                    FROM expenses
                    WHERE category = ? AND date BETWEEN ? AND ?
                """, (category, start_date, end_date))
                
                spent = cur.fetchone()[0]
                percentage = (spent / limit) * 100 if limit > 0 else 0
                remaining = limit - spent
                
                # Generate alert if threshold reached
                if percentage >= 100:
                    budget_alert = {
                        "alert_level": "CRITICAL",
                        "message": f"⚠️ BUDGET EXCEEDED! You have exceeded your budget for '{category}'. Spent: ${spent:.2f} / ${limit:.2f} ({percentage:.1f}%). Over budget by ${abs(remaining):.2f}.",
                        "category": category,
                        "spent": round(spent, 2),
                        "limit": round(limit, 2),
                        "remaining": round(remaining, 2),
                        "percentage": round(percentage, 1)
                    }
                elif percentage >= (threshold * 100):
                    budget_alert = {
                        "alert_level": "WARNING",
                        "message": f"⚠️ BUDGET WARNING! You have reached {percentage:.1f}% of your budget for '{category}'. Spent: ${spent:.2f} / ${limit:.2f}. Remaining: ${remaining:.2f}.",
                        "category": category,
                        "spent": round(spent, 2),
                        "limit": round(limit, 2),
                        "remaining": round(remaining, 2),
                        "percentage": round(percentage, 1)
                    }
            
            response = {
                "status": "ok",
                "id": expense_id,
                "message": "Expense added successfully"
            }
            
            if budget_alert:
                response["budget_alert"] = budget_alert
            
            return response
            
    except Exception as e:
        return {"status": "error", "message": f"Failed to add expense: {str(e)}"}
    
@mcp.tool()
def list_expenses(start_date: str, end_date: str, category: Optional[str] = None):
    """List expense entries within an inclusive date range, optionally filtered by category.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        category: Optional category filter
    
    Returns:
        List of expense entries or error message
    """
    try:
        # Validate dates
        if not validate_date(start_date) or not validate_date(end_date):
            return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
        
        with sqlite3.connect(DB_PATH) as c:
            query = """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += " ORDER BY date DESC, id DESC"
            
            cur = c.execute(query, params)
            cols = [d[0] for d in cur.description]
            expenses = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            return {
                "status": "ok",
                "count": len(expenses),
                "expenses": expenses
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to list expenses: {str(e)}"}

@mcp.tool()
def summarize(start_date: str, end_date: str, category: Optional[str] = None):
    """Summarize expenses by category within an inclusive date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        category: Optional category filter
    
    Returns:
        Summary of expenses by category
    """
    try:
        if not validate_date(start_date) or not validate_date(end_date):
            return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
        
        with sqlite3.connect(DB_PATH) as c:
            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) as count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = c.execute(query, params)
            cols = [d[0] for d in cur.description]
            summary = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            total = sum(item['total_amount'] for item in summary)
            
            return {
                "status": "ok",
                "start_date": start_date,
                "end_date": end_date,
                "total_amount": total,
                "categories": summary
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to summarize: {str(e)}"}

@mcp.tool()
def delete_expense(id: Optional[int] = None, ids: Optional[List[int]] = None, 
                  start_date: Optional[str] = None, end_date: Optional[str] = None,
                  category: Optional[str] = None, delete_all: bool = False):
    """Delete expense entries flexibly - single, multiple, by date range, or all.
    
    Args:
        id: Single expense ID to delete
        ids: List of expense IDs to delete multiple entries
        start_date: Start date for range deletion (YYYY-MM-DD)
        end_date: End date for range deletion (YYYY-MM-DD)
        category: Category filter for deletion
        delete_all: Set to True to delete ALL expenses (use with caution!)
    
    Returns:
        Success status with count of deleted expenses
    
    Examples:
        delete_expense(id=5)  # Delete one
        delete_expense(ids=[1,2,3])  # Delete multiple
        delete_expense(start_date="2026-01-01", end_date="2026-01-31")  # Delete date range
        delete_expense(category="food", start_date="2026-02-01", end_date="2026-02-28")  # Category + date
        delete_expense(delete_all=True)  # Delete everything
    """
    try:
        with sqlite3.connect(DB_PATH) as c:
            conditions = []
            params = []
            
            # Single ID
            if id is not None:
                cur = c.execute("SELECT id FROM expenses WHERE id = ?", (id,))
                if not cur.fetchone():
                    return {"status": "error", "message": f"Expense with id {id} not found"}
                c.execute("DELETE FROM expenses WHERE id = ?", (id,))
                c.commit()
                return {"status": "ok", "message": f"Expense {id} deleted successfully", "deleted_count": 1}
            
            # Multiple IDs
            if ids is not None and len(ids) > 0:
                placeholders = ','.join('?' * len(ids))
                query = f"SELECT COUNT(*) FROM expenses WHERE id IN ({placeholders})"
                cur = c.execute(query, ids)
                count = cur.fetchone()[0]
                
                if count == 0:
                    return {"status": "error", "message": "No expenses found with the provided IDs"}
                
                delete_query = f"DELETE FROM expenses WHERE id IN ({placeholders})"
                c.execute(delete_query, ids)
                c.commit()
                return {
                    "status": "ok", 
                    "message": f"{count} expense(s) deleted successfully",
                    "deleted_count": count
                }
            
            # Date range or category or delete all
            if start_date is not None and end_date is not None:
                if not validate_date(start_date) or not validate_date(end_date):
                    return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
                conditions.append("date BETWEEN ? AND ?")
                params.extend([start_date, end_date])
            
            if category is not None:
                conditions.append("category = ?")
                params.append(category)
            
            if delete_all and not conditions:
                # Delete everything - require explicit confirmation
                cur = c.execute("SELECT COUNT(*) FROM expenses")
                count = cur.fetchone()[0]
                
                if count == 0:
                    return {"status": "error", "message": "No expenses to delete"}
                
                c.execute("DELETE FROM expenses")
                c.commit()
                return {
                    "status": "ok",
                    "message": f"All {count} expenses deleted",
                    "deleted_count": count,
                    "warning": "All expense data has been cleared"
                }
            
            if conditions:
                where_clause = " AND ".join(conditions)
                count_query = f"SELECT COUNT(*) FROM expenses WHERE {where_clause}"
                cur = c.execute(count_query, params)
                count = cur.fetchone()[0]
                
                if count == 0:
                    return {"status": "error", "message": "No expenses found matching the criteria"}
                
                delete_query = f"DELETE FROM expenses WHERE {where_clause}"
                c.execute(delete_query, params)
                c.commit()
                return {
                    "status": "ok",
                    "message": f"{count} expense(s) deleted successfully",
                    "deleted_count": count
                }
            
            return {"status": "error", "message": "No deletion criteria provided. Specify id, ids, date range, category, or delete_all=True"}
            
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete expense: {str(e)}"}

@mcp.tool()
def update_expense(id: int, date: Optional[str] = None, amount: Optional[float] = None, 
                  category: Optional[str] = None, subcategory: Optional[str] = None, 
                  note: Optional[str] = None):
    """Update an existing expense entry. Only provided fields will be updated.
    
    Args:
        id: Expense ID to update
        date: New date in YYYY-MM-DD format (optional)
        amount: New amount (optional)
        category: New category (optional)
        subcategory: New subcategory (optional)
        note: New note (optional)
    
    Returns:
        Success status or error message
    """
    try:
        with sqlite3.connect(DB_PATH) as c:
            # Check if expense exists
            cur = c.execute("SELECT id FROM expenses WHERE id = ?", (id,))
            if not cur.fetchone():
                return {"status": "error", "message": f"Expense with id {id} not found"}
            
            # Validate inputs
            if date is not None and not validate_date(date):
                return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
            
            if amount is not None and not validate_amount(amount):
                return {"status": "error", "message": "Amount must be a positive number"}
            
            if category is not None:
                cat_validation = validate_category(category, subcategory or "")
                if not cat_validation["valid"]:
                    return {"status": "error", "message": cat_validation["error"]}
            
            # Build dynamic update query
            updates = []
            params = []
            
            if date is not None:
                updates.append("date = ?")
                params.append(date)
            if amount is not None:
                updates.append("amount = ?")
                params.append(float(amount))
            if category is not None:
                updates.append("category = ?")
                params.append(category)
            if subcategory is not None:
                updates.append("subcategory = ?")
                params.append(subcategory)
            if note is not None:
                updates.append("note = ?")
                params.append(note)
            
            if not updates:
                return {"status": "error", "message": "No fields provided to update"}
            
            params.append(id)
            query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
            c.execute(query, params)
            c.commit()
            
            return {"status": "ok", "message": f"Expense {id} updated successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to update expense: {str(e)}"}

# Advanced Analytics Tools

@mcp.tool()
def get_monthly_trends(year: int, category: Optional[str] = None):
    """Get monthly spending trends for a specific year.
    
    Args:
        year: Year to analyze (e.g., 2026)
        category: Optional category filter
    
    Returns:
        Monthly breakdown of expenses
    """
    try:
        with sqlite3.connect(DB_PATH) as c:
            query = """
                SELECT strftime('%m', date) as month, 
                       SUM(amount) as total,
                       COUNT(*) as count,
                       AVG(amount) as average
                FROM expenses
                WHERE strftime('%Y', date) = ?
            """
            params = [str(year)]
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += " GROUP BY month ORDER BY month ASC"
            
            cur = c.execute(query, params)
            cols = [d[0] for d in cur.description]
            trends = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            # Add month names
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            for trend in trends:
                trend['month_name'] = month_names[int(trend['month']) - 1]
                trend['total'] = round(trend['total'], 2)
                trend['average'] = round(trend['average'], 2)
            
            return {
                "status": "ok",
                "year": year,
                "category": category if category else "all",
                "trends": trends
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get trends: {str(e)}"}

@mcp.tool()
def get_top_expenses(start_date: str, end_date: str, limit: int = 10):
    """Get the top N expenses within a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Number of top expenses to return (default 10)
    
    Returns:
        List of top expenses sorted by amount
    """
    try:
        if not validate_date(start_date) or not validate_date(end_date):
            return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
        
        with sqlite3.connect(DB_PATH) as c:
            query = """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY amount DESC
                LIMIT ?
            """
            cur = c.execute(query, (start_date, end_date, limit))
            cols = [d[0] for d in cur.description]
            expenses = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            return {
                "status": "ok",
                "count": len(expenses),
                "top_expenses": expenses
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get top expenses: {str(e)}"}

@mcp.tool()
def get_category_breakdown(start_date: str, end_date: str):
    """Get detailed breakdown of expenses by category and subcategory.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Hierarchical breakdown of expenses
    """
    try:
        if not validate_date(start_date) or not validate_date(end_date):
            return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
        
        with sqlite3.connect(DB_PATH) as c:
            query = """
                SELECT category, subcategory, 
                       SUM(amount) as total,
                       COUNT(*) as count,
                       AVG(amount) as average
                FROM expenses
                WHERE date BETWEEN ? AND ?
                GROUP BY category, subcategory
                ORDER BY category, total DESC
            """
            cur = c.execute(query, (start_date, end_date))
            
            # Organize by category
            breakdown = {}
            for row in cur.fetchall():
                cat, subcat, total, count, avg = row
                if cat not in breakdown:
                    breakdown[cat] = {
                        "total": 0,
                        "count": 0,
                        "subcategories": []
                    }
                
                breakdown[cat]["total"] += total
                breakdown[cat]["count"] += count
                breakdown[cat]["subcategories"].append({
                    "subcategory": subcat,
                    "total": round(total, 2),
                    "count": count,
                    "average": round(avg, 2)
                })
            
            # Round totals
            for cat in breakdown:
                breakdown[cat]["total"] = round(breakdown[cat]["total"], 2)
            
            return {
                "status": "ok",
                "start_date": start_date,
                "end_date": end_date,
                "breakdown": breakdown
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get breakdown: {str(e)}"}

# Budget Management Tools

@mcp.tool()
def set_budget(category: str, monthly_limit: float, alert_threshold: float = 0.8):
    """Set a monthly budget limit for a category.
    
    Args:
        category: Category to set budget for
        monthly_limit: Monthly spending limit
        alert_threshold: Alert when spending exceeds this percentage (0.0-1.0)
    
    Returns:
        Success status or error message
    """
    try:
        if not validate_amount(monthly_limit):
            return {"status": "error", "message": "Monthly limit must be a positive number"}
        
        if not (0 < alert_threshold <= 1):
            return {"status": "error", "message": "Alert threshold must be between 0 and 1"}
        
        cat_validation = validate_category(category)
        if not cat_validation["valid"]:
            return {"status": "error", "message": cat_validation["error"]}
        
        with sqlite3.connect(DB_PATH) as c:
            c.execute("""
                INSERT OR REPLACE INTO budgets (category, monthly_limit, alert_threshold)
                VALUES (?, ?, ?)
            """, (category, float(monthly_limit), alert_threshold))
            c.commit()
            
            return {
                "status": "ok",
                "message": f"Budget set for {category}: ${monthly_limit}/month (alert at {int(alert_threshold*100)}%)"
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to set budget: {str(e)}"}

@mcp.tool()
def get_budget_status(year_month: str):
    """Get budget status for a specific month (YYYY-MM format).
    
    Args:
        year_month: Month in YYYY-MM format (e.g., '2026-02')
    
    Returns:
        Budget status for all categories with budgets
    """
    try:
        # Validate format
        try:
            datetime.strptime(year_month, "%Y-%m")
        except ValueError:
            return {"status": "error", "message": "Invalid format. Use YYYY-MM"}
        
        start_date = f"{year_month}-01"
        # Get last day of month
        if year_month.endswith("02"):
            year = int(year_month[:4])
            last_day = "29" if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else "28"
        elif year_month.endswith(("04", "06", "09", "11")):
            last_day = "30"
        else:
            last_day = "31"
        end_date = f"{year_month}-{last_day}"
        
        with sqlite3.connect(DB_PATH) as c:
            # Get all budgets
            cur = c.execute("SELECT category, monthly_limit, alert_threshold FROM budgets")
            budgets = cur.fetchall()
            
            if not budgets:
                return {"status": "ok", "message": "No budgets set", "budgets": []}
            
            status_list = []
            for category, limit, threshold in budgets:
                # Get spending for this category
                cur = c.execute("""
                    SELECT COALESCE(SUM(amount), 0) as spent, COUNT(*) as count
                    FROM expenses
                    WHERE category = ? AND date BETWEEN ? AND ?
                """, (category, start_date, end_date))
                
                spent, count = cur.fetchone()
                percentage = (spent / limit) * 100 if limit > 0 else 0
                remaining = limit - spent
                
                alert_status = "ok"
                if percentage >= 100:
                    alert_status = "exceeded"
                elif percentage >= (threshold * 100):
                    alert_status = "warning"
                
                status_list.append({
                    "category": category,
                    "limit": round(limit, 2),
                    "spent": round(spent, 2),
                    "remaining": round(remaining, 2),
                    "percentage": round(percentage, 1),
                    "alert_status": alert_status,
                    "transaction_count": count
                })
            
            return {
                "status": "ok",
                "month": year_month,
                "budgets": status_list
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get budget status: {str(e)}"}

@mcp.tool()
def list_budgets():
    """List all configured budgets.
    
    Returns:
        List of all budget configurations
    """
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute("SELECT category, monthly_limit, alert_threshold FROM budgets ORDER BY category")
            budgets = []
            for row in cur.fetchall():
                budgets.append({
                    "category": row[0],
                    "monthly_limit": round(row[1], 2),
                    "alert_threshold": row[2]
                })
            
            return {
                "status": "ok",
                "count": len(budgets),
                "budgets": budgets
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to list budgets: {str(e)}"}

@mcp.tool()
def delete_budget(category: str):
    """Delete a budget for a specific category.
    
    Args:
        category: Category to remove budget from
    
    Returns:
        Success status or error message
    """
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute("SELECT category FROM budgets WHERE category = ?", (category,))
            if not cur.fetchone():
                return {"status": "error", "message": f"No budget found for category '{category}'"}
            
            c.execute("DELETE FROM budgets WHERE category = ?", (category,))
            c.commit()
            
            return {"status": "ok", "message": f"Budget deleted for {category}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete budget: {str(e)}"}

# Recurring Expenses

@mcp.tool()
def add_recurring_expense(amount: float, category: str, frequency: str, start_date: str,
                         subcategory: str = "", note: str = "", end_date: Optional[str] = None):
    """Add a recurring expense that will be automatically applied. The first instance is immediately added to expenses.
    
    Args:
        amount: Expense amount
        category: Category
        frequency: 'daily', 'weekly', 'monthly', or 'yearly'
        start_date: Start date in YYYY-MM-DD format
        subcategory: Optional subcategory
        note: Optional note
        end_date: Optional end date in YYYY-MM-DD format
    
    Returns:
        Success status with recurring expense ID and first expense ID
    """
    try:
        if not validate_amount(amount):
            return {"status": "error", "message": "Amount must be a positive number"}
        
        if not validate_date(start_date):
            return {"status": "error", "message": "Invalid start date format. Use YYYY-MM-DD"}
        
        if end_date and not validate_date(end_date):
            return {"status": "error", "message": "Invalid end date format. Use YYYY-MM-DD"}
        
        if frequency not in ['daily', 'weekly', 'monthly', 'yearly']:
            return {"status": "error", "message": "Frequency must be: daily, weekly, monthly, or yearly"}
        
        cat_validation = validate_category(category, subcategory)
        if not cat_validation["valid"]:
            return {"status": "error", "message": cat_validation["error"]}
        
        with sqlite3.connect(DB_PATH) as c:
            # Add to recurring_expenses table
            cur = c.execute("""
                INSERT INTO recurring_expenses 
                (amount, category, subcategory, note, frequency, start_date, end_date, last_applied)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (float(amount), category, subcategory, note, frequency, start_date, end_date, start_date))
            recurring_id = cur.lastrowid
            
            # Add first instance to expenses table
            recurring_note = f"[Recurring {frequency}] {note}" if note else f"Recurring {frequency} expense"
            cur = c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (start_date, float(amount), category, subcategory, recurring_note)
            )
            expense_id = cur.lastrowid
            c.commit()
            
            # Check budget status for this category
            year_month = start_date[:7]  # Extract YYYY-MM from date
            budget_alert = None
            
            # Get budget for this category if it exists
            cur = c.execute(
                "SELECT monthly_limit, alert_threshold FROM budgets WHERE category = ?",
                (category,)
            )
            budget_row = cur.fetchone()
            
            if budget_row:
                limit, threshold = budget_row
                
                # Calculate month boundaries
                month_start = f"{year_month}-01"
                if year_month.endswith("02"):
                    year = int(year_month[:4])
                    last_day = "29" if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else "28"
                elif year_month.endswith(("04", "06", "09", "11")):
                    last_day = "30"
                else:
                    last_day = "31"
                month_end = f"{year_month}-{last_day}"
                
                # Get total spending for this category in the month
                cur = c.execute("""
                    SELECT COALESCE(SUM(amount), 0) as spent
                    FROM expenses
                    WHERE category = ? AND date BETWEEN ? AND ?
                """, (category, month_start, month_end))
                
                spent = cur.fetchone()[0]
                percentage = (spent / limit) * 100 if limit > 0 else 0
                remaining = limit - spent
                
                # Generate alert if threshold reached
                if percentage >= 100:
                    budget_alert = {
                        "alert_level": "CRITICAL",
                        "message": f"⚠️ BUDGET EXCEEDED! You have exceeded your budget for '{category}'. Spent: ${spent:.2f} / ${limit:.2f} ({percentage:.1f}%). Over budget by ${abs(remaining):.2f}.",
                        "category": category,
                        "spent": round(spent, 2),
                        "limit": round(limit, 2),
                        "remaining": round(remaining, 2),
                        "percentage": round(percentage, 1)
                    }
                elif percentage >= (threshold * 100):
                    budget_alert = {
                        "alert_level": "WARNING",
                        "message": f"⚠️ BUDGET WARNING! You have reached {percentage:.1f}% of your budget for '{category}'. Spent: ${spent:.2f} / ${limit:.2f}. Remaining: ${remaining:.2f}.",
                        "category": category,
                        "spent": round(spent, 2),
                        "limit": round(limit, 2),
                        "remaining": round(remaining, 2),
                        "percentage": round(percentage, 1)
                    }
            
            response = {
                "status": "ok",
                "recurring_id": recurring_id,
                "first_expense_id": expense_id,
                "message": f"Recurring expense added: ${amount} {frequency} starting {start_date}. First expense recorded."
            }
            
            if budget_alert:
                response["budget_alert"] = budget_alert
            
            return response
    except Exception as e:
        return {"status": "error", "message": f"Failed to add recurring expense: {str(e)}"}

@mcp.tool()
def list_recurring_expenses(active_only: bool = True):
    """List all recurring expenses.
    
    Args:
        active_only: If True, only show active recurring expenses
    
    Returns:
        List of recurring expenses
    """
    try:
        with sqlite3.connect(DB_PATH) as c:
            query = """
                SELECT id, amount, category, subcategory, note, frequency, 
                       start_date, end_date, last_applied, active
                FROM recurring_expenses
            """
            if active_only:
                query += " WHERE active = 1"
            query += " ORDER BY id DESC"
            
            cur = c.execute(query)
            cols = [d[0] for d in cur.description]
            recurring = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            return {
                "status": "ok",
                "count": len(recurring),
                "recurring_expenses": recurring
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to list recurring expenses: {str(e)}"}

@mcp.tool()
def deactivate_recurring_expense(id: int):
    """Deactivate a recurring expense.
    
    Args:
        id: Recurring expense ID
    
    Returns:
        Success status or error message
    """
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute("SELECT id FROM recurring_expenses WHERE id = ?", (id,))
            if not cur.fetchone():
                return {"status": "error", "message": f"Recurring expense with id {id} not found"}
            
            c.execute("UPDATE recurring_expenses SET active = 0 WHERE id = ?", (id,))
            c.commit()
            
            return {"status": "ok", "message": f"Recurring expense {id} deactivated"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to deactivate recurring expense: {str(e)}"}

# Bulk Operations

@mcp.tool()
def export_to_file(start_date: str, end_date: str, filename: str, format: str = "csv"):
    """Export expenses directly to a CSV or JSON file that can be opened in Excel or other apps.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        filename: Output filename (e.g., 'expenses_feb_2026.csv' or 'expenses.json')
        format: 'json' or 'csv' (default: csv)
    
    Returns:
        Success status with file path
    """
    try:
        if not validate_date(start_date) or not validate_date(end_date):
            return {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}
        
        if format not in ['json', 'csv']:
            return {"status": "error", "message": "Format must be 'json' or 'csv'"}
        
        # Auto-add extension if not present
        if not filename.endswith(('.csv', '.json')):
            filename += f'.{format}'
        
        # Create file path in the same directory as the database
        file_path = os.path.join(os.path.dirname(__file__), filename)
        
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute("""
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date ASC
            """, (start_date, end_date))
            
            cols = [d[0] for d in cur.description]
            expenses = [dict(zip(cols, r)) for r in cur.fetchall()]
            
            if len(expenses) == 0:
                return {
                    "status": "error",
                    "message": f"No expenses found between {start_date} and {end_date}"
                }
            
            if format == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(expenses, f, indent=2)
            else:  # CSV
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=cols)
                    writer.writeheader()
                    # Format dates properly for Excel
                    for expense in expenses:
                        # Ensure date is formatted correctly
                        if expense.get('date'):
                            expense['date'] = str(expense['date'])
                    writer.writerows(expenses)
            
            return {
                "status": "ok",
                "message": f"Exported {len(expenses)} expenses to {format.upper()} file",
                "file_path": file_path,
                "count": len(expenses),
                "format": format
            }
    except Exception as e:
        return {"status": "error", "message": f"Failed to export to file: {str(e)}"}

# Resources and Prompts

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    """Provides the list of available expense categories and subcategories."""
    try:
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.prompt()
def analyze_spending():
    """Analyze my spending patterns and provide insights."""
    return """Please analyze my spending patterns:
1. Show me my monthly trends for the current year
2. Identify my top 5 expense categories
3. Check if I'm within budget for the current month
4. Suggest areas where I could reduce spending"""

@mcp.prompt()
def monthly_report():
    """Generate a comprehensive monthly expense report."""
    return """Generate a monthly report for the current month including:
1. Total spending and comparison to previous month
2. Category breakdown with percentages
3. Budget status for all categories
4. Top 10 largest expenses
5. Daily average spending"""

@mcp.prompt()
def setup_budgets():
    """Help me set up budgets for my expense categories."""
    return """Help me set up monthly budgets:
1. Show my average spending per category over the last 3 months
2. Suggest reasonable budget limits based on my patterns
3. Set up budgets with 80% alert thresholds
4. Explain how to track my progress"""

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")