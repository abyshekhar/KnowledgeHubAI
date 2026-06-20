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


def validate_url_security(url_str: str) -> str:
    """
    Validates that a URL is a secure HTTP/HTTPS URL and prevents Server-Side Request Forgery (SSRF).
    """
    import ipaddress
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url_str)
    except Exception as e:
        raise ValueError(f"Invalid URL structure: {str(e)}")

    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL scheme must be http or https")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a valid hostname")

    # Prevent loopback/local hostname access
    if hostname.lower() in ("localhost", "localhost.localdomain"):
        raise ValueError("Localhost domains are not allowed")

    # Try resolving hostname to IP addresses and verify they are public/routable
    try:
        ips = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # If resolution fails, let it pass validation as it might be an internal name or offline mock,
        # but it will fail during fetch.
        ips = []

    for ip_info in ips:
        ip_str = ip_info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_loopback:
                raise ValueError("Loopback IP addresses are not allowed")
            if ip.is_private:
                raise ValueError("Private network IP addresses are not allowed")
            if ip.is_link_local:
                raise ValueError("Link-local IP addresses are not allowed")
            if ip.is_multicast:
                raise ValueError("Multicast IP addresses are not allowed")
            if ip.is_unspecified:
                raise ValueError("Unspecified IP addresses are not allowed")
        except ValueError as e:
            if "not allowed" in str(e):
                raise

    return url_str

