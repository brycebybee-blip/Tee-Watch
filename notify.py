from __future__ import annotations

import os

import requests

RESEND_URL = "https://api.resend.com/emails"


def send_email(subject: str, html: str) -> None:
    api_key = os.environ["RESEND_API_KEY"].strip()
    to_addr = os.environ["NOTIFY_TO"].strip()
    from_addr = os.environ.get("NOTIFY_FROM", "tee-watch@resend.dev").strip()

    r = requests.post(
        RESEND_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"from": from_addr, "to": [to_addr], "subject": subject, "html": html},
        timeout=15,
    )
    r.raise_for_status()
