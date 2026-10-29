"""Explicit local maintenance command; no HTTP reset endpoint."""

import argparse
import hashlib
from . import store
from .domain import normalized
from .samples import demo_seed


def main():
    parser = argparse.ArgumentParser(
        description="Remove synthetic demo cases; preserve merchant invoices."
    )
    parser.add_argument("--yes", action="store_true", help="Confirm deletion of synthetic records")
    args = parser.parse_args()
    if not args.yes:
        parser.error("Pass --yes to confirm removing synthetic cases. Stop the server first.")
    # Load .env before choosing the DB, as the API does.
    import os
    from dotenv import load_dotenv

    load_dotenv()
    store.DB_PATH = os.getenv("MUNAFA_DB", ".data/munafa.db")
    store.init()
    synthetic = [c for c in store.all_cases() if c["synthetic"]]
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for c in synthetic:
            for resolution in c["resolutions"]:
                db.execute(
                    "DELETE FROM resolution_keys WHERE supplier=? AND reference=?",
                    (
                        normalized(resolution["supplier"]),
                        normalized(resolution["evidence_reference"]),
                    ),
                )
                proof = db.execute(
                    "SELECT data FROM attachments WHERE id=?", (resolution["attachment_id"],)
                ).fetchone()
                if proof:
                    db.execute(
                        "DELETE FROM resolution_proofs WHERE supplier=? AND digest=?",
                        (
                            normalized(resolution["supplier"]),
                            hashlib.sha256(bytes(proof["data"])).hexdigest(),
                        ),
                    )
            db.execute(
                "DELETE FROM synthetic_proofs WHERE attachment_id IN (SELECT id FROM attachments WHERE case_id=?)",
                (c["id"],),
            )
            db.execute("DELETE FROM attachments WHERE case_id=?", (c["id"],))
            db.execute("DELETE FROM cases WHERE id=?", (c["id"],))
    demo_seed()
    print(f"Removed {len(synthetic)} synthetic cases. Merchant invoices were preserved.")


if __name__ == "__main__":
    main()
