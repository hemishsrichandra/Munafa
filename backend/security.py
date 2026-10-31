"""Request authentication, CSRF, bounded rate limits and transactional idempotency."""

import asyncio
import weakref
import hashlib
import json
import os
import time
import uuid
from collections import defaultdict, deque
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select, insert, text
from . import auth, store, models as m
from .db import engine

buckets = defaultdict(deque)
# Per-event-loop limits keep the synchronous connection pool and worker pool available
# for accepted requests to commit while other requests wait for a connection/lock.
request_slots = weakref.WeakKeyDictionary()


def slots_for_loop():
    loop = asyncio.get_running_loop()
    if loop not in request_slots:
        request_slots[loop] = asyncio.Semaphore(8)
    return request_slots[loop]


def origins():
    configured = os.getenv("APP_ORIGINS", "")
    if configured:
        return [v.strip() for v in configured.split(",") if v.strip()]
    if os.getenv("APP_ENV", "production") == "production":
        return []
    return [
        f"http://{host}:{port}"
        for host in ("localhost", "127.0.0.1")
        for port in (5173, 4173, 8000, 8001)
    ]


def rate_limit(key, limit):
    now = time.monotonic()
    q = buckets[key]
    while q and q[0] < now - 60:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(429, "Too many requests. Wait a minute and try again.")
    q.append(now)
    if len(buckets) > 10000:
        for k in list(buckets):
            if not buckets[k] or buckets[k][-1] < now - 60:
                del buckets[k]


def permission(path, method):
    if path in ("/api/auth/logout", "/api/auth/security", "/api/auth/recovery-codes"):
        return "read"  # Own-account controls apply to viewers too, never ledger authority.
    if method == "GET":
        return "export" if path == "/api/export" else "read"
    if path.endswith(("/approve", "/resolve", "/sent", "/execute")):
        return "approve"
    if path.endswith("/message"):
        return "messaging"
    return "write"


async def bounded_body(request, limit):
    """Bound streamed/chunked requests before allocating a complete body.

    Starlette's cached request replays _body to the downstream parser. This is
    intentionally done before database checkout/provider calls.
    """
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, "Request is too large.")
        chunks.append(chunk)
    request._body = b"".join(chunks)
    return request._body


async def guard(request, call_next):
    path = request.url.path
    write = request.method not in ("GET", "HEAD", "OPTIONS")
    token_ctx = None
    db_ctx = None
    conn = None
    transaction = None
    slots = None
    try:
        if request.method == "OPTIONS":
            return await call_next(request)
        if path.startswith("/api/"):
            waiting_slots = slots_for_loop()
            await waiting_slots.acquire()
            slots = waiting_slots
            if write:
                origin = request.headers.get("origin")
                if origin and origin not in origins():
                    raise HTTPException(403, "Origin not permitted.")
                length = request.headers.get("content-length")
                if length:
                    try:
                        size = int(length)
                    except ValueError:
                        raise HTTPException(400, "Invalid request length.") from None
                    if size < 0:
                        raise HTTPException(400, "Invalid request length.")
                    if size > 9 * 1024 * 1024:
                        raise HTTPException(413, "Request is too large.")
            public = path in (
                "/api/health",
                "/api/auth/login",
                "/api/auth/dev-login",
                "/api/auth/signup",
                "/api/auth/demo",
                "/api/auth/recover",
            )
            if public:
                if write:
                    host = request.client.host if request.client else "unknown"
                    rate_limit(("login", host), 10)
                    if path in ("/api/auth/signup", "/api/auth/demo", "/api/auth/recover"):
                        rate_limit(("provision", host), 3)
                    await bounded_body(request, 16384)
            else:
                bearer = request.headers.get("authorization", "")
                token = (
                    bearer[7:]
                    if bearer.startswith("Bearer ")
                    else request.cookies.get("pbp_session", "")
                )
                if not token:
                    raise HTTPException(401, "Sign in to continue.")
                if path == "/api/auth/recovery-codes":
                    rate_limit(
                        ("recovery-codes", request.client.host if request.client else "unknown"), 3
                    )
                p = await run_in_threadpool(
                    auth.authenticate,
                    token,
                    request.headers.get("x-csrf-token", "")
                    if write and not bearer.startswith("Bearer ")
                    else None,
                )
                token_ctx = auth.principal.set(p)
                auth.current(permission(path, request.method))
                rate_limit(("api", p.user_id), 120)
                if write:
                    body = await bounded_body(
                        request, 16384 if path.startswith("/api/auth/") else 9 * 1024 * 1024
                    )
                conn = await run_in_threadpool(engine().connect)
                transaction = conn.begin()
                db_ctx = store.request_connection.set(conn)
                key = request.headers.get("idempotency-key")
                if write and not path.startswith("/api/auth/"):
                    if not key or len(key) > 100:
                        raise HTTPException(400, "A valid Idempotency-Key is required.")
                    rate_limit(("write", p.user_id), 60)
                    fingerprint = hashlib.sha256(
                        request.method.encode() + path.encode() + body
                    ).hexdigest()
                    # Store-scoped transaction lock serializes identical operation IDs, including first inserts.
                    await run_in_threadpool(
                        conn.execute,
                        text("SELECT pg_advisory_xact_lock(:key)"),
                        {
                            "key": int.from_bytes(
                                hashlib.sha256((p.store_id + key).encode()).digest()[:8],
                                "big",
                                signed=True,
                            )
                        },
                    )
                    existing = (
                        conn.execute(
                            select(m.operations).where(
                                store.scope(m.operations), m.operations.c.operation_key == key
                            )
                        )
                        .mappings()
                        .first()
                    )
                    if existing:
                        if (
                            existing["actor_id"] != p.user_id
                            or existing["request_digest"] != fingerprint
                        ):
                            raise HTTPException(
                                409,
                                "This operation key was already used with different content or actor.",
                            )
                        response = JSONResponse(
                            existing["response"], status_code=existing["status_code"]
                        )
                        response.headers["Idempotency-Replayed"] = "true"
                        await run_in_threadpool(transaction.commit)
                        return headers(response)
            response = await call_next(request)
            if conn is not None:
                data = b"".join([chunk async for chunk in response.body_iterator])
                if response.status_code < 400:
                    if (
                        write
                        and key
                        and not path.startswith("/api/auth/")
                        and "application/json" in response.headers.get("content-type", "")
                    ):
                        conn.execute(
                            insert(m.operations).values(
                                id=uuid.uuid4().hex,
                                store_id=p.store_id,
                                actor_id=p.user_id,
                                operation_key=key,
                                request_digest=fingerprint,
                                response=json.loads(data),
                                status_code=response.status_code,
                                at=__import__("datetime").datetime.now(
                                    __import__("datetime").timezone.utc
                                ),
                            )
                        )
                    await run_in_threadpool(transaction.commit)
                else:
                    await run_in_threadpool(transaction.rollback)
                rebuilt = Response(data, status_code=response.status_code)
                rebuilt.raw_headers = list(response.raw_headers)
                response = rebuilt
            return headers(response)
        return headers(await call_next(request))
    except HTTPException as exc:
        return headers(JSONResponse({"detail": exc.detail}, status_code=exc.status_code))
    except Exception:
        if os.getenv("APP_ENV") == "test":
            raise
        # Do not serialize SQL, credentials, request bodies or driver errors to clients.
        return headers(
            JSONResponse(
                {"detail": "The operation could not complete. Reload and retry."}, status_code=503
            )
        )
    finally:
        if transaction is not None and transaction.is_active:
            await run_in_threadpool(transaction.rollback)
        if db_ctx is not None:
            store.request_connection.reset(db_ctx)
        if conn is not None:
            await run_in_threadpool(conn.close)
        if token_ctx is not None:
            auth.principal.reset(token_ctx)
        if slots is not None:
            slots.release()


def headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=(self)"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    )
    if os.getenv("APP_ENV", "production") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
