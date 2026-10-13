"""Load the demo calls into the database.

Run from the project root:

    python -m scripts.seed_demo            # add demo calls if the database is empty
    python -m scripts.seed_demo --reset    # delete ALL evaluations, then add demo calls
    python -m scripts.seed_demo --keep-dates

Calls are scored with the rule-based mock evaluator (instant, no API key needed).
"""

import argparse

from app.config import DATABASE_URL
from app.database import SessionLocal, init_db
from app.seed_data import SEED_CALLS
from app.services.seeding import seed_demo_data


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Load fictional demo calls into the CallFlow database.")
    parser.add_argument("--reset", action="store_true", help="delete all existing evaluations first")
    parser.add_argument(
        "--keep-dates", action="store_true", help="keep the original call dates instead of ending on today"
    )
    args = parser.parse_args(argv)

    init_db()
    with SessionLocal() as db:
        added = seed_demo_data(db, reset=args.reset, shift_dates=not args.keep_dates)
    if added:
        print(f"Added {added} demo calls to {DATABASE_URL}.")
    else:
        print(
            f"The database ({DATABASE_URL}) already has evaluations; nothing added. "
            f"Use --reset to replace them with the {len(SEED_CALLS)} demo calls."
        )


if __name__ == "__main__":
    main()
