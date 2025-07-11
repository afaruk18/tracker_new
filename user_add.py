#!/usr/bin/env python3
"""Command-line tool to add a *Person* record to the database.

Usage example:
    uv run user.py \
        --full-name "Ahmet Faruk Çetinkaya" \
        --preferred-name "Faruk" \
        --github-user afaruk18 \
        --jira-user None \
        --gcal-user ahmetfarukcetinkaya290@gmail.com \
        --computer-user faruk

Running the script multiple times with the *same* external usernames will fail
because the corresponding columns are unique.  Specify a different username or
update the existing record in the database if needed.
"""

import argparse
import sys
from typing import Any, Dict

from tracker.db.connect import get_session
from tracker.tables.people_table import Person_Usernames


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # noqa: D401
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="Add a person to the database")
    p.add_argument("--full-name", required=True, help="Full legal name")
    p.add_argument("--preferred-name", help="Preferred display name (nickname)")
    p.add_argument("--github-user", help="GitHub username")
    p.add_argument("--jira-user", help="Jira username")
    p.add_argument("--gcal-user", help="Google Calendar username / email")
    p.add_argument("--computer-user", help="Local computer (OS) account username")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    ns = parse_args(argv)

    # Build the new *Person* row dynamically to avoid passing None for every field
    fields: Dict[str, Any] = {
        "full_name": ns.full_name,
        "preferred_name": ns.preferred_name,
        "github_user": ns.github_user,
        "jira_user": ns.jira_user,
        "gcal_user": ns.gcal_user,
        "computer_user": ns.computer_user,
    }
    # Remove keys with *None* values so SQL defaults can apply
    person_kwargs = {k: v for k, v in fields.items() if v is not None}

    person = Person_Usernames(**person_kwargs)

    with get_session() as session:
        session.add(person)
        session.commit()
        session.refresh(person)

    print(f"✔ Added person_id={person.person_id} – {person.full_name}")


if __name__ == "__main__":
    main(sys.argv[1:])