import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import click
from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'adopter',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS animals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(120) NOT NULL,
    species VARCHAR(40) NOT NULL,
    age VARCHAR(40),
    size VARCHAR(30),
    description TEXT,
    health TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS adoptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    animal_id INTEGER NOT NULL,
    adopter_id INTEGER NOT NULL,
    message TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animals(id),
    FOREIGN KEY (adopter_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adoption_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (adoption_id) REFERENCES adoptions(id)
);
CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL,
    animal_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, animal_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (animal_id) REFERENCES animals(id)
);
CREATE TABLE IF NOT EXISTS donations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    donor_id INTEGER NOT NULL,
    kind VARCHAR(30) NOT NULL,
    amount DECIMAL(10, 2),
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donor_id) REFERENCES users(id)
);
"""

MYSQL_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL,
    email VARCHAR(180) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'adopter', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS animals (
    id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL,
    species VARCHAR(40) NOT NULL, age VARCHAR(40), size VARCHAR(30), description TEXT,
    health TEXT, status VARCHAR(20) NOT NULL DEFAULT 'available', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS adoptions (
    id INT AUTO_INCREMENT PRIMARY KEY, animal_id INT NOT NULL, adopter_id INT NOT NULL,
    message TEXT, status VARCHAR(20) NOT NULL DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (animal_id) REFERENCES animals(id), FOREIGN KEY (adopter_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY, adoption_id INT NOT NULL,
    rating INT NOT NULL, comment TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (adoption_id) REFERENCES adoptions(id)
);
CREATE TABLE IF NOT EXISTS favorites (
    user_id INT NOT NULL,
    animal_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, animal_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (animal_id) REFERENCES animals(id)
);
CREATE TABLE IF NOT EXISTS donations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donor_id INT NOT NULL,
    kind VARCHAR(30) NOT NULL,
    amount DECIMAL(10, 2),
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donor_id) REFERENCES users(id)
);
"""


def _mysql_config(url):
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username,
        "password": parsed.password,
        "database": parsed.path.lstrip("/"),
    }


def get_db():
    if "db" not in g:
        url = current_app.config.get("DATABASE_URL", "")
        if url.startswith(("postgres://", "postgresql://")):
            import psycopg2
            g.db = psycopg2.connect(url, connect_timeout=10, options="-c search_path=caopanheiro")
        elif url.startswith("mysql://"):
            import mysql.connector
            g.db = mysql.connector.connect(**_mysql_config(url))
        else:
            path = current_app.config.get(
                "DATABASE", str(Path(current_app.instance_path) / "caopanheiro.sqlite3")
            )
            g.db = sqlite3.connect(path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def database_kind():
    url = current_app.config.get("DATABASE_URL", "")
    if url.startswith(("postgres://", "postgresql://")):
        return "postgres"
    if url.startswith("mysql://"):
        return "mysql"
    if url:
        raise ValueError("DATABASE_URL deve usar postgres://, postgresql:// ou mysql://.")
    return "sqlite"


def adapt_sql(query):
    if database_kind() != "sqlite":
        query = query.replace("?", "%s")
    if database_kind() == "postgres":
        query = query.replace(" LIKE ", " ILIKE ")
    return query


def insert_row(cursor, query, args):
    # All generated IDs must use RETURNING on PostgreSQL, including atomic flows.
    match = re.match(r"\s*INSERT INTO (\w+)", query, re.I)
    returning = database_kind() == "postgres" and match and match[1].lower() != "favorites"
    if returning:
        query = query.rstrip().rstrip(";") + " RETURNING id"
    cursor.execute(adapt_sql(query), args)
    return cursor.fetchone()[0] if returning else cursor.lastrowid


def query_db(query, args=(), one=False):
    db = get_db()
    kind = database_kind()
    if kind == "postgres":
        from psycopg2.extras import RealDictCursor
        cursor = db.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = db.cursor(dictionary=True) if kind == "mysql" else db.cursor()
    try:
        cursor.execute(adapt_sql(query), args)
        rows = cursor.fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        cursor.close()


def execute_db(query, args=()):
    db = get_db()
    cursor = db.cursor()
    try:
        if query.lstrip().upper().startswith("INSERT"):
            last_id = insert_row(cursor, query, args)
        else:
            cursor.execute(adapt_sql(query), args)
            last_id = None
        db.commit()
        return last_id
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


def init_postgres(db):
    cursor = db.cursor()
    try:
        # Serialize automatic startup migrations across Gunicorn workers/deploys.
        cursor.execute("SELECT pg_advisory_xact_lock(784021965)")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS caopanheiro")
        schema = SCHEMA.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        for statement in schema.split(";"):
            if statement.strip():
                cursor.execute(statement)
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='caopanheiro' AND table_name='donations' AND column_name='contact'")
        legacy_donations = cursor.fetchone() is None
        columns = {
            "users": {"photo_filename": "VARCHAR(255)"},
            "animals": {"photo_filename": "VARCHAR(255)", "breed": "VARCHAR(80)", "sex": "VARCHAR(30)", "vaccinated": "VARCHAR(30)", "neutered": "VARCHAR(30)"},
            "adoptions": {"answers": "TEXT"},
            "donations": {"contact": "VARCHAR(180)"},
        }
        for table, fields in columns.items():
            for name, kind in fields.items():
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {kind}")
        if legacy_donations:
            cursor.execute("UPDATE donations SET status='pending' WHERE status='received'")
        cursor.execute("ALTER TABLE donations ALTER COLUMN status SET DEFAULT 'pending'")
        cursor.execute("""CREATE TABLE IF NOT EXISTS donation_events (
            id SERIAL PRIMARY KEY, donation_id INTEGER NOT NULL REFERENCES donations(id),
            actor_id INTEGER REFERENCES users(id), status VARCHAR(20) NOT NULL,
            note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # Application data stays out of Supabase's exposed public schema.
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()


def _split_schema():
    return [statement.strip() for statement in SCHEMA.split(";") if statement.strip()]


@click.command("init-db")
def init_db():
    database_kind()  # Validate URLs rather than silently opening SQLite.
    db = get_db()
    if database_kind() == "postgres":
        init_postgres(db)
        click.echo("Banco PostgreSQL inicializado.")
        return
    schema = MYSQL_SCHEMA if current_app.config.get("DATABASE_URL", "").startswith("mysql://") else SCHEMA
    for statement in [item.strip() for item in schema.split(";") if item.strip()]:
        if current_app.config.get("DATABASE_URL", "").startswith("mysql://"):
            cursor = db.cursor()
            cursor.execute(statement)
            cursor.close()
        else:
            db.execute(statement)
    if current_app.config.get("DATABASE_URL", "").startswith("mysql://"):
        cursor = db.cursor()
        cursor.execute("SHOW COLUMNS FROM animals LIKE 'photo_filename'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE animals ADD COLUMN photo_filename VARCHAR(255)")
        cursor.close()
    else:
        columns = db.execute("PRAGMA table_info(animals)").fetchall()
        if not any(column[1] == "photo_filename" for column in columns):
            db.execute("ALTER TABLE animals ADD COLUMN photo_filename VARCHAR(255)")
    if current_app.config.get("DATABASE_URL", "").startswith("mysql://"):
        cursor = db.cursor()
        cursor.execute("SHOW COLUMNS FROM adoptions LIKE 'status'")
        status_column = cursor.fetchone()
        if status_column and status_column[1].startswith("enum"):
            cursor.execute("ALTER TABLE adoptions MODIFY COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'")
        cursor.execute("SHOW COLUMNS FROM adoptions LIKE 'answers'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE adoptions ADD COLUMN answers TEXT")
        cursor.close()
    else:
        columns = db.execute("PRAGMA table_info(adoptions)").fetchall()
        if not any(column[1] == "answers" for column in columns):
            db.execute("ALTER TABLE adoptions ADD COLUMN answers TEXT")
    if current_app.config.get("DATABASE_URL", "").startswith("mysql://"):
        cursor = db.cursor()
        cursor.execute("SHOW COLUMNS FROM users LIKE 'photo_filename'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN photo_filename VARCHAR(255)")
        cursor.close()
    else:
        columns = db.execute("PRAGMA table_info(users)").fetchall()
        if not any(column[1] == "photo_filename" for column in columns):
            db.execute("ALTER TABLE users ADD COLUMN photo_filename VARCHAR(255)")
    mysql = current_app.config.get("DATABASE_URL", "").startswith("mysql://")
    cursor = db.cursor()
    if mysql:
        cursor.execute("SHOW COLUMNS FROM donations LIKE 'contact'")
        legacy_donations = not cursor.fetchone()
    else:
        legacy_donations = not any(column[1] == "contact" for column in db.execute("PRAGMA table_info(donations)").fetchall())
    if legacy_donations:
        cursor.execute("ALTER TABLE donations ADD COLUMN contact VARCHAR(180)")
        # The previous version labeled intentions as received without confirmation.
        cursor.execute("UPDATE donations SET status='pending' WHERE status='received'")
    if mysql:
        cursor.execute("ALTER TABLE donations ALTER COLUMN status SET DEFAULT 'pending'")
    event_id = "INT AUTO_INCREMENT PRIMARY KEY" if mysql else "INTEGER PRIMARY KEY AUTOINCREMENT"
    cursor.execute(f"""CREATE TABLE IF NOT EXISTS donation_events (
        id {event_id}, donation_id INT NOT NULL, actor_id INT,
        status VARCHAR(20) NOT NULL, note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (donation_id) REFERENCES donations(id),
        FOREIGN KEY (actor_id) REFERENCES users(id)
    )""")
    cursor.close()
    extra_fields = {"breed": "VARCHAR(80)", "sex": "VARCHAR(30)", "vaccinated": "VARCHAR(30)", "neutered": "VARCHAR(30)"}
    for name, kind in extra_fields.items():
        if current_app.config.get("DATABASE_URL", "").startswith("mysql://"):
            cursor = db.cursor()
            cursor.execute("SHOW COLUMNS FROM animals LIKE %s", (name,))
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE animals ADD COLUMN {name} {kind}")
            cursor.close()
        else:
            columns = db.execute("PRAGMA table_info(animals)").fetchall()
            if not any(column[1] == name for column in columns):
                db.execute(f"ALTER TABLE animals ADD COLUMN {name} {kind}")
    db.commit()
    click.echo("Banco inicializado.")
