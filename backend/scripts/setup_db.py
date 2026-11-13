"""Create internee_eval database on the Render Postgres instance and enable pgvector."""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv
import os

load_dotenv(ROOT / ".env")

ADMIN_URL = os.getenv("POSTGRES_URL", "").strip()
DB_NAME = "internee_eval"


def normalize_admin_url(url: str) -> str:
    if not url:
        raise SystemExit("POSTGRES_URL is missing")
    parsed = urlparse(url)
    # Connect to default `postgres` db for CREATE DATABASE
    path = "/postgres"
    query = parsed.query
    if "sslmode" not in query:
        query = "sslmode=require" if not query else f"{query}&sslmode=require"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", query, ""))


def main() -> None:
    admin_url = normalize_admin_url(ADMIN_URL)
    print(f"Connecting to admin DB… host={urlparse(admin_url).hostname}")

    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            exists = cur.fetchone() is not None
            if exists:
                print(f"Database `{DB_NAME}` already exists")
            else:
                cur.execute(f'CREATE DATABASE "{DB_NAME}"')
                print(f"Created database `{DB_NAME}`")

    # Enable extension on the new DB
    target = urlparse(admin_url)._replace(path=f"/{DB_NAME}")
    target_url = urlunparse(target)
    with psycopg.connect(target_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                print("pgvector extension ready")
            except Exception as exc:
                print(f"WARNING: could not enable pgvector: {exc}")
            cur.execute("SELECT current_database(), version()")
            db, version = cur.fetchone()
            print(f"Connected OK -> database={db}")
            print(f"Postgres: {version.split(',')[0]}")


if __name__ == "__main__":
    main()
