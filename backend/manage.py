"""Explicit identity provisioning and non-destructive demo seed commands."""

import argparse
import getpass
from . import auth


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create-owner", "seed-demo"])
    parser.add_argument("--username", default="")
    args = parser.parse_args()
    if args.command == "create-owner":
        username = args.username or input("Username: ").strip()
        password = getpass.getpass("New password (12+ characters): ")
        if len(password) < 12:
            parser.error("Use at least 12 characters.")
        auth.provision(username, password, input("Store name: ").strip() or "Kirana store")
        print("Owner created. Sign in with the supplied username and password.")
    else:
        if not auth.development_login():
            parser.error("Explicit development login configuration is required.")
        result = auth.demo_login(__import__("os").environ["DEV_LOGIN_CODE"])
        token = auth.principal.set(result[0])
        try:
            from .samples import demo_seed

            demo_seed()
            print("Synthetic demo store seeded without deleting existing records.")
        finally:
            auth.principal.reset(token)


if __name__ == "__main__":
    main()
