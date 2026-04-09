# 💰 Expense Tracker MCP Server

A Model Context Protocol (MCP) server for managing personal expenses with budget tracking, analytics, and smart alerts.

[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-blue)](https://github.com/jlowin/fastmcp)
[![Python](https://img.shields.io/badge/python-3.13+-brightgreen)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/)
[![SQLite](https://img.shields.io/badge/database-SQLite3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

## ✨ Features

- 💸 **Expense Management** — Add, update, delete, and list expenses with smart categorization
- 📊 **Analytics** — Monthly trends, top expenses, and category breakdowns
- 💰 **Budget Tracking** — Set budgets with automatic alerts when thresholds are reached
- 🔄 **Recurring Expenses** — Automatic tracking of regular bills (first instance auto-added)
- 📤 **Data Export** — Export to CSV/JSON files for external analysis
- ✅ **Smart Validation** — Comprehensive input validation and error handling
- 🐳 **Docker Ready** — Ships as a pre-built Docker image for instant local use

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| MCP Framework | **FastMCP** |
| Language | **Python 3.13+** |
| Database (local) | **SQLite3** |
| Database (async/remote) | **aiosqlite** |
| Packaging / Deps | **uv** |
| Containerization | **Docker** |

---

## 📁 Project Structure

```
Expense Tracker MCP server/
│
├── local_mcp_server.py          # Synchronous MCP server (stdio, for local Claude Desktop use)
├── remote_mcp_server_async.py   # Async MCP server (for remote/cloud deployments)
├── categories.json              # Predefined expense categories and subcategories
├── expenses.db                  # SQLite database (auto-generated, gitignored)
├── pyproject.toml               # Project metadata and dependencies
│
└── Expense Tracker MCP server dockerized/
    ├── local_mcp_server.py      # Same server, bundled for Docker image build
    ├── Dockerfile               # Docker image definition
    ├── .dockerignore            # Files excluded from Docker build context
    ├── categories.json
    ├── pyproject.toml
    └── uv.lock
```

---

## 🐳 Docker Image

A pre-built Docker image is available. Pull and run it without any local Python setup:

```bash
# Pull the image
docker pull coder8710/expense-tracker-mcp-server

# Run the container (stdio mode for Claude Desktop)
docker run -i --rm coder8710/expense-tracker-mcp-server
```

### Connect to Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "expense-tracker": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "coder8710/expense-tracker-mcp-server"
      ]
    }
  }
}
```

> **Note:** The database (`expenses.db`) lives inside the container. To persist data across runs, mount a volume:
> ```bash
> docker run -i --rm -v expense-data:/app coder8710/expense-tracker-mcp-server
> ```

---

## 🗂️ Server Variants

### `local_mcp_server.py` — Local / Docker (stdio)

> **Use this for Claude Desktop or any MCP client on your machine.**

- Uses **synchronous SQLite3** — simple, zero dependencies beyond FastMCP
- FastMCP runs in **stdio transport** mode — Claude Desktop communicates via stdin/stdout
- Bundled and shipped as part of the Docker image
- Entry point: `uv run local_mcp_server.py`

**Run locally:**
```bash
uv run local_mcp_server.py
```

---

### `remote_mcp_server_async.py` — Remote / Cloud (async)

> **Use this when deploying to a cloud environment (e.g., Railway, Render, FastMCP Cloud).**

- Fully **async** using `aiosqlite` — handles concurrent requests efficiently
- Automatically detects a writable directory for the database:
  - Uses `DATA_DIR` environment variable if set
  - Falls back to the script's directory, then `/tmp` as last resort
- Designed for **remote HTTP/SSE transport** deployments

**Run locally for testing:**
```bash
uv run remote_mcp_server_async.py
```

**Deploy to cloud:** Set the `DATA_DIR` environment variable to a persistent volume path if your platform uses ephemeral filesystems.

---

## 🛠️ Available MCP Tools

### Expense Management (5)
| Tool | Description |
|---|---|
| `add_expense` | Add a new expense with automatic budget alerts |
| `list_expenses` | List expenses filtered by date range and/or category |
| `update_expense` | Update any field of an existing expense |
| `delete_expense` | Delete by ID, multiple IDs, date range, category, or all |
| `summarize` | Category-wise spending summary with totals |

### Analytics (3)
| Tool | Description |
|---|---|
| `get_monthly_trends` | Monthly spending trends for a specific year |
| `get_top_expenses` | Highest expenses within a date range |
| `get_category_breakdown` | Hierarchical breakdown by category and subcategory |

### Budget Management (4)
| Tool | Description |
|---|---|
| `set_budget` | Set a monthly budget limit with alert threshold |
| `get_budget_status` | Check budget status for a specific month (YYYY-MM) |
| `list_budgets` | View all configured budgets |
| `delete_budget` | Remove a budget for a category |

### Recurring Expenses (3)
| Tool | Description |
|---|---|
| `add_recurring_expense` | Create a recurring expense (auto-adds first instance) |
| `list_recurring_expenses` | View all recurring expenses (active or all) |
| `deactivate_recurring_expense` | Disable a recurring expense |

### Data Export (1)
| Tool | Description |
|---|---|
| `export_to_file` | Export expenses to CSV or JSON file |

**Total: 16 MCP Tools**

---

## 🏷️ Categories

Predefined categories defined in `categories.json`:

| Category | Subcategories |
|---|---|
| **Food** | groceries, dining out, coffee, snacks |
| **Transport** | fuel, public transport, parking, tolls |
| **Housing** | rent, maintenance, utilities, repairs |
| **Health** | medicines, doctor visits, diagnostics |
| **Entertainment** | movies, streaming, sports, hobbies |
| **Shopping** | clothing, electronics, personal care |
| **Insurance** | life, vehicle, home, health |
| **Education** | books, courses, subscriptions |

---

## 🎯 Key Capabilities

### Smart Budget Alerts
When you add an expense, the server automatically checks if you're approaching or exceeding your budget limit for that category. You receive instant alerts when you cross set thresholds (default: 80%).

### Automatic Recurring Tracking
Setting up a recurring expense immediately creates the first instance in your expense list. Supports `daily`, `weekly`, `monthly`, and `yearly` frequencies.

### Flexible Data Operations
Delete expenses individually, in bulk by date range, by category, or all at once. Update any single field without touching others. Filter and search across multiple dimensions.

### Comprehensive Analytics
Track spending patterns over time with monthly trends, identify top expenses, and get detailed breakdowns showing exactly where your money goes.

### Data Portability
Export financial data to **CSV** or **JSON** format for further analysis in spreadsheets or other tools.

---

## 📊 Use Cases

- Track daily personal expenses with smart categorization
- Monitor spending against monthly budgets with threshold alerts
- Analyze financial trends and monthly patterns
- Manage recurring bills and subscriptions
- Export data for external financial planning tools
- Get AI-powered insights through natural language queries via Claude
