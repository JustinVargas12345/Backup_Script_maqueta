import base64
import json
import hmac
import hashlib
import time
import logging
from typing import Optional, Tuple

import requests

logger = logging.getLogger("dbbackup")


def _b64url_encode(data: bytes) -> str:
    s = base64.urlsafe_b64encode(data).decode("utf-8")
    return s.rstrip("=")


def make_jwt(secret: str, claims: Optional[dict] = None) -> str:
    """Create a simple HS256 JWT using the provided secret.

    This avoids adding PyJWT as dependency; suitable for simple signing.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    claims = claims or {}
    now = int(time.time())
    payload = {"iat": now, **claims}

    header_b = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b}.{payload_b}".encode("utf-8")

    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b = _b64url_encode(sig)
    return f"{header_b}.{payload_b}.{sig_b}"


def send_notification(url: str, payload: dict, secret: Optional[str] = None, auth_token: Optional[str] = None, timeout: int = 10) -> Tuple[bool, int, str]:
    """Send a POST with JSON payload to `url`.

    If `secret` is provided, a JWT will be created and sent in the
    `Authorization: Bearer <token>` header.

    Returns (ok, status_code, text).
    """
    headers = {"Content-Type": "application/json"}
    # auth_token: already-signed bearer token (passed directly)
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    elif secret:
        try:
            token = make_jwt(secret)
            headers["Authorization"] = f"Bearer {token}"
        except Exception as e:
            logger.exception(f"Error creando JWT para notificación: {e}")

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        ok = 200 <= r.status_code < 300
        if not ok:
            logger.warning(f"Notification POST returned {r.status_code}: {r.text}")
        else:
            logger.info(f"Notification POST succeeded {r.status_code}")
        return ok, r.status_code, r.text
    except Exception as e:
        logger.exception(f"Error enviando notificación POST a {url}: {e}")
        return False, -1, str(e)
