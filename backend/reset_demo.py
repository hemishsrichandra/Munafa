"""Legacy reset disabled: do not delete user records as part of application startup."""

if __name__ == "__main__":
    raise SystemExit(
        "Reset is disabled. Use a fresh PostgreSQL demo store via the documented seed command. Existing data is preserved."
    )
