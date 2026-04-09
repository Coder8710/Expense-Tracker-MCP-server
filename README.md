# 💰 Expense Tracker MCP Server

A Model Context Protocol (MCP) server for managing personal expenses with budget tracking, analytics, and smart alerts.

[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-blue)](https://github.com/jlowin/fastmcp)
[![Python](https://img.shields.io/badge/python-3.13+-brightgreen)](https://www.python.org/)

## ✨ Features

- 💸 **Expense Management** - Add, update, delete, and list expenses with smart categorization
- 📊 **Analytics** - Monthly trends, top expenses, and category breakdowns
- 💰 **Budget Tracking** - Set budgets with automatic alerts when thresholds are reached
- 🔄 **Recurring Expenses** - Automatic tracking of regular bills (first instance auto-added)
- 📤 **Data Export** - Export to CSV/JSON files for external analysis
- ✅ **Smart Validation** - Comprehensive input validation and error handling
## 🔧 Tech Stack

**Core Framework**
- **FastMCP** - Model Context Protocol server framework
- **Python 3.13+** - Modern Python 

**Database**
- **SQLite3** - Lightweight embedded database for local storage
## 📁 Project Files

**local_mcp_server.py**  
The core MCP server implementation containing all 16 tools, database initialization, validation logic, and MCP resource/prompt definitions. Uses synchronous SQLite3 and runs over stdio transport — ideal for local use with Claude Desktop. This is the entry point that starts the FastMCP server and handles all expense operations.

**remote_mcp_server_async.py**  
An async variant of the server built with `aiosqlite` for efficient concurrent database access. Designed for remote and cloud deployments. Automatically detects a writable directory for the database using the `DATA_DIR` environment variable, falling back to the script directory or `/tmp` as needed.

**categories.json**  
Predefined expense categories and subcategories used for validation and organization. This file ensures consistent categorization across all expenses and can be customized to add new categories or subcategories as needed.

**expenses.db** (auto-generated)  
SQLite database file created automatically on first run. Stores all expense transactions, budget configurations, and recurring expense definitions. Protected by .gitignore to keep your financial data private.

## 🐳 Docker Image

A pre-built Docker image of this local mcp server is available on Docker Hub — no local Python setup required (The Docker image is public , also you can explore how docker image is built in "Expense Tracker MCP server dockerized" directory in this Github repository).
Create docker container then you can use this MCP server with Claude Desktop.

```bash
docker pull coder980/expense-tracker-mcp-server
```



## 🗂️ Available MCP Tools

### Expense Management Tools (5)
1. **add_expense** - Add new expense with automatic budget checking and alerts
2. **list_expenses** - List expenses with date range and category filters
3. **update_expense** - Update any field of an existing expense
4. **delete_expense** - Delete by ID, multiple IDs, date range, category, or all
5. **summarize** - Get category-wise spending summary with totals

### Analytics Tools (3)
6. **get_monthly_trends** - Monthly spending trends for a specific year
7. **get_top_expenses** - Find highest expenses in a date range
8. **get_category_breakdown** - Hierarchical breakdown by category and subcategory

### Budget Management Tools (4)
9. **set_budget** - Set monthly budget limits with alert thresholds
10. **get_budget_status** - Check budget status for a specific month (YYYY-MM)
11. **list_budgets** - View all configured budgets
12. **delete_budget** - Remove a budget for a category

### Recurring Expenses Tools (3)
13. **add_recurring_expense** - Create recurring expense (auto-adds first instance to expenses)
14. **list_recurring_expenses** - View all recurring expenses (active/all)
15. **deactivate_recurring_expense** - Disable a recurring expense

### Data Export Tools (1)
16. **export_to_file** - Export expenses to CSV or JSON file

**Total: 16 MCP Tools**

## 🏷️ Categories

The system supports predefined expense categories including:
- **Food** - groceries, dining out, coffee, snacks
- **Transport** - fuel, public transport, parking, tolls
- **Housing** - rent, maintenance, utilities, repairs
- **Health** - medicines, doctor visits, diagnostics
- **Entertainment** - movies, streaming, sports, hobbies
- **Shopping** - clothing, electronics, personal care
- **Insurance** - life, vehicle, home, health
- **Education** - books, courses, subscriptions

## 🎯 Key Capabilities

### Smart Budget Management
When you add an expense, the system automatically checks if you're approaching or exceeding your budget limits for that category. You receive instant alerts when you cross set thresholds (default 80%).

### Automatic Recurring Tracking
Setting up a recurring expense automatically creates the first instance in your expense list. The system tracks monthly, weekly, daily, or yearly recurring bills.

### Flexible Data Operations
Delete expenses individually, in bulk by date range, by category, or all at once. Update any field of an expense without affecting others. Filter and search expenses across multiple dimensions.

### Comprehensive Analytics
Track spending patterns over time with monthly trends, identify top expenses, and get detailed category breakdowns showing exactly where your money goes.

### Data Portability
Export your financial data to CSV or JSON format for further analysis in spreadsheets or other tools.

## 📊 Use Cases

- Track daily personal expenses with categorization
- Monitor spending against monthly budgets
- Analyze financial trends and patterns
- Manage recurring bills and subscriptions
- Export data for financial planning
- Get AI-powered insights through natural language queries
