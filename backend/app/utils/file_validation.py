
from pathlib import Path


MAX_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024

DOCUMENT_TYPES = {
    "ID_PROOF",
    "CONTRACT",
    "CERTIFICATE",
    "RESUME",
    "OTHER",
}

ALLOWED_SIGNATURES = {
    ".pdf": ("application/pdf", lambda data: data.startswith(b"%PDF-")),
    ".png": (
        "image/png",
        lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    ),
    ".jpg": (
        "image/jpeg",
        lambda data: data.startswith(b"\xff\xd8\xff"),
    ),
    ".jpeg": (
        "image/jpeg",
        lambda data: data.startswith(b"\xff\xd8\xff"),
    ),
}


def validate_document_upload(
    filename: str | None,
    content: bytes,
) -> tuple[str, str, str]:
    if not filename or not filename.strip():
        raise ValueError("A filename is required.")

    # Treat both Windows and POSIX separators as path separators.
    safe_name = filename.replace("\\", "/").split("/")[-1].strip()

    if (
        not safe_name
        or safe_name in {".", ".."}
        or any(ord(char) < 32 for char in safe_name)
    ):
        raise ValueError("Invalid filename.")

    if len(safe_name) > 255:
        raise ValueError("Filename cannot exceed 255 characters.")

    if not content:
        raise ValueError("The uploaded file is empty.")

    if len(content) > MAX_DOCUMENT_SIZE_BYTES:
        raise ValueError("File size cannot exceed 5 MB.")

    extension = Path(safe_name).suffix.lower()

    signature_rule = ALLOWED_SIGNATURES.get(extension)

    if signature_rule is None:
        raise ValueError(
            "Unsupported file type. Upload a PDF, JPG, JPEG, or PNG file."
        )

    content_type, signature_check = signature_rule

    if not signature_check(content):
        raise ValueError(
            "The file content does not match its filename extension."
        )

    return safe_name, content_type, extension
