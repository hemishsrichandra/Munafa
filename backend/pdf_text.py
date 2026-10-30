"""Isolated, bounded PDF text-layer helper. No network, OCR or app/database imports."""

import io
import json
import sys
import resource
from pypdf import PdfReader

try:
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    data = sys.stdin.buffer.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("PDF too large")
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDF needs manual review")
    if len(reader.pages) > 10:
        raise ValueError("Use a PDF of at most ten pages")
    pages = []
    remaining = 18000
    for i, page in enumerate(reader.pages):
        text = (page.extract_text() or "")[:remaining]
        remaining -= len(text)
        pages.append({"page": i + 1, "text": text})
        if remaining <= 0:
            break
    print(json.dumps({"page_count": len(reader.pages), "pages": pages}))
except Exception:
    print(
        json.dumps(
            {
                "page_count": None,
                "pages": [],
                "error": "PDF text could not be read safely. Enter the invoice manually; the original file is preserved.",
            }
        )
    )
