# PostgreSQL Setup Guide

## 1. Install PostgreSQL
- Windows: Download from https://www.postgresql.org/download/windows/
- During installation, set a password for the `postgres` user

## 2. Create Database
Open PostgreSQL command line (psql) or pgAdmin and run:

```sql
CREATE DATABASE server_monitor;
```

## 3. Set Environment Variables
Copy `.env.example` to `.env` and update with your credentials:

```bash
cp .env.example .env
```

Edit `.env` file:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=server_monitor
DB_USER=postgres
DB_PASSWORD=your_postgres_password
```

## 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```

## 5. Load Environment Variables (Windows PowerShell)
```powershell
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="server_monitor"
$env:DB_USER="postgres"
$env:DB_PASSWORD="your_password"
```

Or use python-dotenv in your app.py:
```python
from dotenv import load_dotenv
load_dotenv()
```

## 6. Run the Application
```bash
python app.py
```

The application will automatically create the required tables on first run.

## Default Login
- Username: `admin`
- Password: `admin123`
