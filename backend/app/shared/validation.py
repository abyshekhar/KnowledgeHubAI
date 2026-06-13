from __future__ import annotations


def normalize_email_identifier(value: str) -> str:
    email = value.strip()
    if len(email) > 255:
        raise ValueError("Email must be 255 characters or fewer")
    if email.count("@") != 1:
        raise ValueError("Email must contain one @ sign")
    if any(character.isspace() for character in email):
        raise ValueError("Email must not contain whitespace")

    local_part, domain = email.rsplit("@", 1)
    if not local_part or not domain:
        raise ValueError("Email must include a local part and domain")
    if "." not in domain:
        raise ValueError("Email domain must include a suffix")

    labels = domain.split(".")
    if any(not label for label in labels):
        raise ValueError("Email domain contains an empty label")
    return f"{local_part.lower()}@{domain.lower()}"
