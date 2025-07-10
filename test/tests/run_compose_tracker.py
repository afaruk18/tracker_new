#!/usr/bin/env python
"""Utility script to (re)create the local Postgres stack and briefly run the
ActivityTracker application.

Steps performed:
1. docker compose down -v         # remove containers *and* volumes
2. docker compose up -d          # start services in the background
3. Wait until Postgres is accepting connections using **pg_isready**
4. Run the ActivityTracker for a short period to ensure the code starts fine

Environment for the test run is loaded automatically from
``test/settings/test.env`` if present.  You can override individual variables
by exporting them before invoking the script.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import psycopg
from psycopg import OperationalError


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if key and _:
            os.environ.setdefault(key.strip(), value.strip())


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_ENV_PATH = PROJECT_ROOT / "test" / "settings" / "test.env"

# Add src directory to Python path for the test
sys.path.insert(0, str(PROJECT_ROOT / "src"))

_load_env_file(TEST_ENV_PATH)

RUN_TIME = int(os.environ.get("TRACKER_TEST_RUN_TIME", "10"))
PG_TIMEOUT = int(os.environ.get("TRACKER_PG_TIMEOUT", "30"))


def _run(cmd: list[str] | str, *, check: bool = True) -> None:
    """Wrapper around *subprocess.run* that prints the command first."""
    printable = " ".join(cmd) if isinstance(cmd, list) else cmd
    print(f"\n>> {printable}")
    subprocess.run(cmd, check=check, shell=isinstance(cmd, str))


def _docker_compose(*args: str) -> None:
    """Execute a *docker compose* command with the provided *args*.

    Falls back to ``docker-compose`` (legacy binary) if ``docker compose`` is
    not available.
    """
    cmd_base = ["docker", "compose"]
    if subprocess.run(cmd_base + ["version"], capture_output=True).returncode != 0:
        cmd_base = ["docker-compose"]
    _run(cmd_base + list(args))


def _wait_for_postgres(host: str, port: str, timeout: int = PG_TIMEOUT) -> None:
    """Block until ``pg_isready`` reports Postgres is accepting connections."""
    print(
        f"Waiting for Postgres to become ready on {host}:{port} (timeout={timeout}s)…",
        flush=True,
    )

    start = time.monotonic()

    # Build DSN using available environment variables (defaults are fine for tests)
    user = os.environ.get("PG_USER", "postgres")
    password = os.environ.get("PG_PASS", "postgres")
    database = os.environ.get("PG_DATABASE", "postgres")

    dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}?connect_timeout=1"

    while True:
        # ------------------------------------------------------------------
        # Prefer a *direct* connection attempt via psycopg as this avoids the
        # need for external command-line tools like *pg_isready* (which may
        # not be installed in CI images).  Fall back to the CLI only if the
        # Python driver fails for some unforeseen reason.
        # ------------------------------------------------------------------
        try:
            with psycopg.connect(dsn):
                print("Postgres is ready!", flush=True)
                return
        except OperationalError:
            # Connection refused or not yet accepting – keep waiting
            pass
        except Exception:
            # As a last resort, fall back to pg_isready inside the docker container if present
            # Try to exec into the db service and run pg_isready
            db_service = os.environ.get("PG_SERVICE", "db")
            docker_cmd = ["docker", "compose", "exec", "-T", db_service, "pg_isready", "-h", host, "-p", str(port)]
            result = subprocess.run(docker_cmd, capture_output=True)
            if result.returncode == 0:
                print("Postgres is ready!", flush=True)
                return

        if time.monotonic() - start > timeout:
            raise RuntimeError("Postgres did not become ready within the allotted time")

        time.sleep(1)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def main() -> None:
    os.chdir(PROJECT_ROOT)  # ensure paths are correct regardless of cwd

    # (1) Tear down any existing stack, including named volumes
    _docker_compose("down", "-v")

    # (2) Bring the stack back up in detached mode
    _docker_compose("up", "-d")

    # (3) Wait for Postgres to be ready using pg_isready --------------------
    host = os.environ.get("PG_HOST", "localhost")
    port = os.environ.get("PG_PORT", "5432")
    _wait_for_postgres(host, port)

    # (4) Start the tracker as a subprocess so we can interrupt it later
    print(f"\n>> Running ActivityTracker for {RUN_TIME}s")

    # Use the run_tracker.py script or direct python with PYTHONPATH
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

    tracker_code = "from tracker.core.app import ActivityTracker; ActivityTracker().run()"
    tracker_proc = subprocess.Popen([sys.executable, "-c", tracker_code], cwd=PROJECT_ROOT, env=env)

    try:
        time.sleep(RUN_TIME)
    finally:
        tracker_proc.send_signal(signal.SIGINT)
        tracker_proc.wait()
        print("\nActivityTracker finished the short test run.")


if __name__ == "__main__":
    main()
