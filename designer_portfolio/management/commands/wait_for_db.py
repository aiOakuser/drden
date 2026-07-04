import os
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.management import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:  # pragma: no cover - psycopg2 required for Postgres
    psycopg2 = None
    sql = None


_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}


def _env_truthy(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in _TRUE_VALUES


def _stringify(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


@dataclass(frozen=True)
class DbParams:
    name: str
    user: str
    password: str
    host: str
    port: str


def _db_params() -> DbParams:
    config = settings.DATABASES.get("default", {})
    return DbParams(
        name=_stringify(config.get("NAME") or ""),
        user=_stringify(config.get("USER") or ""),
        password=_stringify(config.get("PASSWORD") or ""),
        host=_stringify(config.get("HOST") or ""),
        port=_stringify(config.get("PORT") or ""),
    )


def _maintenance_db_candidates() -> list[str]:
    candidates: list[str] = []
    env_value = os.getenv("DB_MAINTENANCE_DB") or os.getenv("POSTGRES_MAINTENANCE_DB")
    for name in (env_value, "postgres", "template1"):
        if name and name not in candidates:
            candidates.append(name)
    return candidates


def _is_missing_db_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "does not exist" in message and "database" in message


def _ensure_database_exists(params: DbParams) -> tuple[bool, str | None]:
    if psycopg2 is None or sql is None:
        return False, "psycopg2 is not installed; cannot auto-create the database."
    if not params.name:
        return False, "Database name is empty; cannot auto-create the database."
    if not params.user:
        return False, "Database user is empty; cannot auto-create the database."

    last_error: Exception | None = None
    for maintenance_db in _maintenance_db_candidates():
        conn = None
        try:
            conn = psycopg2.connect(
                dbname=maintenance_db,
                user=params.user,
                password=params.password,
                host=params.host or None,
                port=params.port or None,
                connect_timeout=5,
            )
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (params.name,))
                if cursor.fetchone():
                    return True, f"Database '{params.name}' already exists."
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(params.name)))
            return True, f"Database '{params.name}' created."
        except Exception as exc:
            last_error = exc
            duplicate_error = getattr(getattr(psycopg2, "errors", None), "DuplicateDatabase", None)
            if duplicate_error and isinstance(exc, duplicate_error):
                return True, f"Database '{params.name}' already exists."
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    return False, f"Failed to connect to a maintenance database. Last error: {last_error}"


class Command(BaseCommand):
    help = "Wait for the default database connection to be available."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=int(os.getenv("DB_WAIT_TIMEOUT", "60")),
            help="Max seconds to wait for the database (DB_WAIT_TIMEOUT).",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=float(os.getenv("DB_WAIT_INTERVAL", "2")),
            help="Seconds between retries (DB_WAIT_INTERVAL).",
        )

    def handle(self, *args, **options):
        timeout = max(0, int(options["timeout"]))
        interval = max(0.5, float(options["interval"]))
        deadline = time.monotonic() + timeout
        attempt = 0
        attempted_create = False
        auto_create = _env_truthy("DB_AUTO_CREATE", default=True)

        while True:
            attempt += 1
            try:
                connections["default"].cursor()
            except OperationalError as exc:
                if auto_create and not attempted_create and _is_missing_db_error(exc):
                    attempted_create = True
                    created, message = _ensure_database_exists(_db_params())
                    if message:
                        if created:
                            self.stdout.write(self.style.SUCCESS(message))
                        else:
                            self.stderr.write(self.style.ERROR(message))
                    if created:
                        continue
                if time.monotonic() >= deadline:
                    self.stderr.write(
                        self.style.ERROR(
                            f"Database still unavailable after {timeout}s."
                        )
                    )
                    raise
                self.stdout.write(
                    f"Database unavailable (attempt {attempt}); retrying in {interval}s..."
                )
                time.sleep(interval)
            else:
                self.stdout.write(self.style.SUCCESS("Database is available."))
                break
