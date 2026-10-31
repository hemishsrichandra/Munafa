"""Isolated, bounded PDF text-layer helper. No network, OCR or app/database imports."""

import io
import json
import sys
from pypdf import PdfReader


def text_pages(reader, limit=18000):
    pages, remaining, truncated = [], limit, False
    for i, page in enumerate(reader.pages):
        value = page.extract_text() or ""
        excerpt = value[:remaining]
        pages.append({"page": i + 1, "text": excerpt})
        remaining -= len(excerpt)
        if len(value) > len(excerpt) or (remaining == 0 and i + 1 < len(reader.pages)):
            truncated = True
            break
    return {
        "page_count": len(reader.pages),
        "pages": pages,
        "text_complete": not truncated,
        "truncated": truncated,
    }


def main():
    try:
        try:
            import resource
        except ImportError:  # Windows still has the parent process timeout/byte/page limits.
            resource = None
        if resource is not None:
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
        print(json.dumps(text_pages(reader)))
    except Exception:
        print(
            json.dumps(
                {
                    "page_count": None,
                    "pages": [],
                    "text_complete": False,
                    "error": "PDF text could not be read safely. Enter the invoice manually; the original file is preserved.",
                }
            )
        )


if __name__ == "__main__":
    main()
