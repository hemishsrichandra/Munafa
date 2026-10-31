"""Local release inspection. Reports paths/counts only, never secret values or file contents."""

import ast
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    dist = ROOT / "frontend/dist"
    if not (dist / "index.html").is_file():
        raise SystemExit("Build the production frontend before this audit.")
    config = dotenv_values(ROOT / ".env")
    secrets = {
        key: value
        for key, value in config.items()
        if value
        and len(value) >= 12
        and ("KEY" in key or "PASSWORD" in key or key == "DEV_LOGIN_CODE")
    }
    from sqlalchemy.engine import make_url

    for key in ("DATABASE_URL", "TEST_DATABASE_URL"):
        if config.get(key):
            password = make_url(config[key]).password
            if password and len(password) >= 8:
                secrets[key + "_password"] = password
    tracked = (
        subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
        .stdout.decode()
        .split("\0")
    )
    paths = {ROOT / p for p in tracked if p and (ROOT / p).is_file()}
    paths.update(p for p in dist.rglob("*") if p.is_file())
    # Current new implementation files are included before their first commit.
    paths.update(
        p
        for folder in ("backend", "frontend/src", "scripts")
        for p in (ROOT / folder).rglob("*")
        if p.is_file()
        and "__pycache__" not in str(p)
        and p.suffix in (".py", ".js", ".jsx", ".cjs")
    )
    failures = []
    for path in paths:
        raw = path.read_bytes()
        for key, value in secrets.items():
            if value.encode() in raw:
                failures.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "reason": "private_config_value",
                        "setting": key,
                    }
                )
        if re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", raw):
            failures.append({"file": str(path.relative_to(ROOT)), "reason": "private_key_material"})
    sqlite_imports = []
    for folder in ("backend", "scripts"):
        for path in (ROOT / folder).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else []
                )
                if any(
                    name.split(".")[0] in ("sqlite3", "aiosqlite", "pysqlite3") for name in names
                ):
                    sqlite_imports.append(str(path.relative_to(ROOT)))
    for path in (dist / "assets").glob("*.js"):
        if b"Sync diagnostics (development only)" in path.read_bytes():
            failures.append(
                {"file": str(path.relative_to(ROOT)), "reason": "production_debug_control"}
            )
    from backend.app import app

    endpoints = [
        {
            "method": method.upper(),
            "path": path,
            "authenticated": path
            not in (
                "/api/health",
                "/api/auth/login",
                "/api/auth/dev-login",
                "/api/auth/signup",
                "/api/auth/demo",
            ),
        }
        for path, methods in app.openapi()["paths"].items()
        for method in methods
        if method in ("get", "post", "patch", "put", "delete") and path.startswith("/api/")
    ]
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "files_scanned": len(paths),
        "private_config_values_checked": len(secrets),
        "secret_scan_failures": failures,
        "sqlite_imports": sqlite_imports,
        "production_debug_controls_absent": not any(
            f["reason"] == "production_debug_control" for f in failures
        ),
        "api_endpoints": endpoints,
        "limitations": [
            "Exact private-value and key-material scan, not a full secret scanner or history-forensics review.",
            "No PII classifier or malware/legal certification. No raw file/log content or secret is emitted.",
            "PostgreSQL driver/runtime rejection and tenant tests are verified separately.",
        ],
    }
    output = ROOT / "artifacts/test-evidence"
    output.mkdir(parents=True, exist_ok=True)
    (output / "release-source-audit.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "files_scanned": len(paths),
                "secret_scan_failure_count": len(failures),
                "sqlite_import_count": len(sqlite_imports),
                "endpoint_count": len(endpoints),
            }
        )
    )
    if failures or sqlite_imports:
        raise SystemExit("Release audit failed; inspect the redacted local report.")


if __name__ == "__main__":
    main()
