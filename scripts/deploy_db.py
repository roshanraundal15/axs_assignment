"""Create the demo schema and seed it once for a hosted deployment."""
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from seed_data import main as seed_data

load_dotenv()


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set before database initialization")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        table_exists = connection.execute(
            text("SELECT to_regclass('public.customers') IS NOT NULL")
        ).scalar()

    if not table_exists:
        schema_path = Path(__file__).with_name("init_db.sql")
        with engine.begin() as connection:
            connection.exec_driver_sql(schema_path.read_text(encoding="utf-8"))

    with engine.connect() as connection:
        customer_count = connection.execute(text("SELECT COUNT(*) FROM customers")).scalar()

    if customer_count == 0:
        seed_data()
        print("Database initialized and seeded.")
    else:
        print(f"Database already contains {customer_count} customers; keeping existing data.")


if __name__ == "__main__":
    main()