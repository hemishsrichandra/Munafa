"""Explicit identity provisioning and non-destructive demo seed commands."""

import argparse
import getpass
from . import auth


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=["create-owner", "set-password", "seed-demo", "allow-ai", "deny-ai"]
    )
    parser.add_argument("--username", default="")
    args = parser.parse_args()
    if args.command == "create-owner":
        username = args.username or input("Username: ").strip()
        password = getpass.getpass("New password (12+ characters): ")
        if not 12 <= len(password) <= 200 or not password.strip():
            parser.error("Use a password with 12–200 characters.")
        auth.provision(username, password, input("Store name: ").strip() or "Kirana store")
        print("Owner created. Sign in with the supplied username and password.")
    elif args.command == "set-password":
        username = args.username or input("Exact username: ").strip()
        password = getpass.getpass("New password (12–200 characters): ")
        if password != getpass.getpass("Confirm new password: "):
            parser.error("Passwords do not match. No change made.")
        try:
            auth.change_password(username, password)
        except ValueError as exc:
            parser.error(str(exc))
        print("Password changed. All existing server sessions for this account were revoked.")
    elif args.command in ("allow-ai", "deny-ai"):
        username = args.username or input("Exact username: ").strip()
        enabled = args.command == "allow-ai"
        if input("Type ALLOW to enable provider spending or DENY to disable it: ").strip() != (
            "ALLOW" if enabled else "DENY"
        ):
            parser.error("Confirmation did not match. No change made.")
        try:
            auth.set_provider_access(username, enabled)
        except ValueError as exc:
            parser.error(str(exc))
        print(
            "Provider access updated. Account must still pass provider configuration, roles and request limits."
        )
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
