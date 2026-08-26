-- AXS Multi-Agent RAG Demo Schema
-- 4 interrelated tables with synthetic data

DROP TABLE IF EXISTS sales CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    city VARCHAR(80),
    country VARCHAR(80) DEFAULT 'India',
    signup_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    role VARCHAR(50),
    hire_date DATE NOT NULL,
    salary NUMERIC(12, 2),
    manager_id INTEGER REFERENCES employees(employee_id)
);

CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    project_name VARCHAR(120) NOT NULL,
    customer_id INTEGER REFERENCES customers(customer_id),
    lead_employee_id INTEGER REFERENCES employees(employee_id),
    start_date DATE,
    end_date DATE,
    budget NUMERIC(14, 2),
    status VARCHAR(30) DEFAULT 'active'
);

CREATE TABLE sales (
    sale_id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(customer_id),
    employee_id INTEGER REFERENCES employees(employee_id),
    project_id INTEGER REFERENCES projects(project_id),
    sale_date DATE NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    product VARCHAR(100),
    region VARCHAR(50)
);

-- Indexes for common query patterns
CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_sales_customer ON sales(customer_id);
CREATE INDEX idx_projects_customer ON projects(customer_id);
CREATE INDEX idx_employees_dept ON employees(department);
