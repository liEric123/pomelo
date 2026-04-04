"""
Resume file parsing utilities.

Extracts and normalizes plain text from uploaded resume files.
Supported: PDF (.pdf), DOCX (.docx), plain text (.txt).
"""

import io
import re


ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_RESUME_CHARS = 3000


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Dispatch to the correct extractor, clean output, and cap at MAX_RESUME_CHARS.

    Raises:
        ValueError: unsupported file extension.
        RuntimeError: extraction produced no usable text.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported resume format: .{ext}")

    if ext == "pdf":
        raw = _extract_pdf(file_bytes)
    elif ext == "docx":
        raw = _extract_docx(file_bytes)
    else:  # txt
        raw = file_bytes.decode("utf-8", errors="ignore")

    text = clean_text(raw)
    if not text or len(text) < 50:
        raise RuntimeError("Resume text extraction produced unusable content.")

    return text[:MAX_RESUME_CHARS]


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages)


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from a .docx file using python-docx."""
    import docx

    document = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def clean_text(text: str) -> str:
    """Normalize whitespace and strip resume parsing artifacts.

    - Remove null bytes and non-printable characters (keep newlines/tabs)
    - Strip leading/trailing whitespace per line
    - Collapse runs of blank lines to a single blank line
    """
    # drop non-printable chars except whitespace
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", text)
    # strip each line
    lines = [line.strip() for line in text.splitlines()]
    # collapse 3+ consecutive blank lines → 1
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return cleaned.strip()
