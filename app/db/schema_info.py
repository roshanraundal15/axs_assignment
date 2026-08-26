"""Static schema description used by Schema Agent."""

SCHEMA_DESCRIPTION = """
Database: axs_rag (PostgreSQL)

Tables and columns:

1. customers
   - customer_id (SERIAL PRIMARY KEY)
   - name (VARCHAR)
   - email (VARCHAR UNIQUE)
   - city (VARCHAR)
   - country (VARCHAR, default India)
   - signup_date (DATE)
   - status (VARCHAR: active | inactive)

2. employees
   - employee_id (SERIAL PRIMARY KEY)
   - name (VARCHAR)
   - department (VARCHAR: Engineering, Sales, Support, Finance, Operations)
   - role (VARCHAR: Engineer, Manager, Analyst, Associate)
   - hire_date (DATE)
   - salary (NUMERIC)
   - manager_id (INTEGER, FK -> employees.employee_id)

3. projects
   - project_id (SERIAL PRIMARY KEY)
   - project_name (VARCHAR)
   - customer_id (INTEGER, FK -> customers.customer_id)
   - lead_employee_id (INTEGER, FK -> employees.employee_id)
   - start_date (DATE)
   - end_date (DATE, nullable)
   - budget (NUMERIC)
   - status (VARCHAR: active | completed | on_hold)

4. sales
   - sale_id (SERIAL PRIMARY KEY)
   - customer_id (INTEGER, FK -> customers.customer_id)
   - employee_id (INTEGER, FK -> employees.employee_id)
   - project_id (INTEGER, FK -> projects.project_id, nullable)
   - sale_date (DATE)
   - amount (NUMERIC)
   - product (VARCHAR: Analytics Suite, Cloud License, Support Plan, API Credits, Training)
   - region (VARCHAR: West, South, North, East, Central)

Relationships:
- sales.customer_id -> customers.customer_id
- sales.employee_id -> employees.employee_id
- sales.project_id -> projects.project_id
- projects.customer_id -> customers.customer_id
- projects.lead_employee_id -> employees.employee_id
- employees.manager_id -> employees.employee_id

Notes for temporal queries:
- Use CURRENT_DATE for "today"
- "last year" -> sale_date >= date_trunc('year', CURRENT_DATE) - interval '1 year'
  AND sale_date < date_trunc('year', CURRENT_DATE)
- "Q1 2024" -> sale_date >= '2024-01-01' AND sale_date < '2024-04-01'
"""

TABLE_LIST = ["customers", "employees", "projects", "sales"]
