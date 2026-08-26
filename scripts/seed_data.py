"""Generate and insert synthetic data for AXS Multi-Agent RAG assignment."""
import os
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/axs_rag"
)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

CITIES = ["Mumbai", "Pune", "Bengaluru", "Hyderabad", "Delhi", "Chennai", "Kolkata"]
DEPARTMENTS = ["Engineering", "Sales", "Support", "Finance", "Operations"]
PRODUCTS = ["Analytics Suite", "Cloud License", "Support Plan", "API Credits", "Training"]
REGIONS = ["West", "South", "North", "East", "Central"]
STATUSES = ["active", "completed", "on_hold"]

FIRST = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna",
         "Ananya", "Diya", "Isha", "Myra", "Saanvi", "Aadhya", "Pari", "Anvi"]
LAST = ["Sharma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Nair", "Mehta",
        "Joshi", "Desai", "Iyer", "Chopra", "Malhotra", "Rao", "Shah"]


def rand_name():
    return f"{random.choice(FIRST)} {random.choice(LAST)}"


def rand_date(start_year=2022, end_year=2025):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def main():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        # Clear existing
        for t in ["sales", "projects", "employees", "customers"]:
            conn.execute(text(f"TRUNCATE {t} RESTART IDENTITY CASCADE"))

        # Customers (200)
        customers = []
        for i in range(200):
            name = rand_name()
            email = f"{name.lower().replace(' ', '.')}{i}@example.com"
            city = random.choice(CITIES)
            signup = rand_date(2022, 2025)
            status = random.choice(["active", "active", "active", "inactive"])
            customers.append(
                {"name": name, "email": email, "city": city, "country": "India",
                 "signup_date": signup, "status": status}
            )
        conn.execute(
            text(
                "INSERT INTO customers (name, email, city, country, signup_date, status) "
                "VALUES (:name, :email, :city, :country, :signup_date, :status)"
            ),
            customers,
        )

        # Employees (100)
        employees = []
        for i in range(100):
            employees.append(
                {
                    "name": rand_name(),
                    "department": random.choice(DEPARTMENTS),
                    "role": random.choice(["Engineer", "Manager", "Analyst", "Associate"]),
                    "hire_date": rand_date(2019, 2024),
                    "salary": float(Decimal(random.randint(400000, 2500000))),
                    "manager_id": None,
                }
            )
        conn.execute(
            text(
                "INSERT INTO employees (name, department, role, hire_date, salary, manager_id) "
                "VALUES (:name, :department, :role, :hire_date, :salary, :manager_id)"
            ),
            employees,
        )
        # Assign some managers
        conn.execute(
            text(
                "UPDATE employees SET manager_id = "
                "(SELECT employee_id FROM employees e2 WHERE e2.employee_id < employees.employee_id "
                "AND e2.role = 'Manager' ORDER BY random() LIMIT 1) "
                "WHERE role != 'Manager' AND employee_id > 5"
            )
        )

        # Projects (120)
        projects = []
        for i in range(120):
            start = rand_date(2023, 2025)
            end = start + timedelta(days=random.randint(30, 400)) if random.random() > 0.3 else None
            projects.append(
                {
                    "project_name": f"Project-{i+1:03d}-{random.choice(['Alpha','Beta','Gamma','Delta'])}",
                    "customer_id": random.randint(1, 200),
                    "lead_employee_id": random.randint(1, 100),
                    "start_date": start,
                    "end_date": end,
                    "budget": float(Decimal(random.randint(50000, 5000000))),
                    "status": random.choice(STATUSES),
                }
            )
        conn.execute(
            text(
                "INSERT INTO projects (project_name, customer_id, lead_employee_id, start_date, end_date, budget, status) "
                "VALUES (:project_name, :customer_id, :lead_employee_id, :start_date, :end_date, :budget, :status)"
            ),
            projects,
        )

        # Sales (800)
        sales = []
        for i in range(800):
            sales.append(
                {
                    "customer_id": random.randint(1, 200),
                    "employee_id": random.randint(1, 100),
                    "project_id": random.randint(1, 120) if random.random() > 0.2 else None,
                    "sale_date": rand_date(2023, 2025),
                    "amount": float(Decimal(random.randint(5000, 500000))),
                    "product": random.choice(PRODUCTS),
                    "region": random.choice(REGIONS),
                }
            )
        conn.execute(
            text(
                "INSERT INTO sales (customer_id, employee_id, project_id, sale_date, amount, product, region) "
                "VALUES (:customer_id, :employee_id, :project_id, :sale_date, :amount, :product, :region)"
            ),
            sales,
        )

        counts = {
            t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            for t in ["customers", "employees", "projects", "sales"]
        }
        print("Seeded successfully:", counts)


if __name__ == "__main__":
    main()
