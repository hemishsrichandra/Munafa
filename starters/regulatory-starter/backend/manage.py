"""Explicit local account provisioning, no demo data or automatic seeds."""

import argparse
import getpass
from .auth import provision


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create-owner"])
    parser.parse_args()
    username = input("Username: ").strip()
    name = input("Business name: ").strip()
    password = getpass.getpass("Password (12+ characters): ")
    if not username or len(username) > 120 or not name or len(name) > 120 or len(password) < 12:
        parser.error(
            "Provide a username/business name up to 120 characters and a password of 12+ characters."
        )
    provision(username, password, name, demo=False)
    print("Account created. No regulatory profile, source data or legal result was generated.")


if __name__ == "__main__":
    main()
