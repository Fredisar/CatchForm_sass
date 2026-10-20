"""Notifications e-mail des nouvelles soumissions, via l'API HTTP de Resend.

Désactivées tant que RESEND_API_KEY n'est pas défini. L'envoi part dans un
thread pour ne pas faire attendre le visiteur qui remplit le formulaire.
"""
import json
import threading
import urllib.request
from html import escape

from flask import current_app

from .utils import as_text

RESEND_URL = "https://api.resend.com/emails"


def build_html(form_name, fields, dashboard_url):
    """Corps HTML de l'e-mail ; tout contenu venant du visiteur est échappé."""
    rows = "".join(
        "<tr>"
        f"<td style='padding:6px 14px 6px 0;color:#64748b;vertical-align:top'><b>{escape(str(key))}</b></td>"
        f"<td style='padding:6px 0;white-space:pre-wrap'>{escape(as_text(value))}</td>"
        "</tr>"
        for key, value in fields.items()
    )
    return (
        "<div style='font-family:Arial,sans-serif;font-size:14px;color:#0f172a'>"
        f"<h2 style='margin:0 0 16px'>Nouvelle soumission : {escape(form_name)}</h2>"
        f"<table style='border-collapse:collapse'>{rows}</table>"
        f"<p style='margin-top:24px'><a href='{escape(dashboard_url)}'>Voir dans le tableau de bord</a></p>"
        "</div>"
    )


def send_submission_email(to, form_name, fields, subject, dashboard_url):
    """Planifie l'envoi. Retourne False si les notifications sont désactivées."""
    api_key = current_app.config.get("RESEND_API_KEY")
    if not api_key:
        return False

    message = {
        "from": current_app.config["MAIL_FROM"],
        "to": [to],
        "subject": subject or f"Nouvelle soumission — {form_name}",
        "html": build_html(form_name, fields, dashboard_url),
    }
    # « Répondre » dans la messagerie écrit directement au visiteur.
    visitor_email = fields.get("email")
    if isinstance(visitor_email, str) and "@" in visitor_email:
        message["reply_to"] = visitor_email.strip()

    threading.Thread(
        target=_post, args=(api_key, message, current_app.logger), daemon=True
    ).start()
    return True


def _post(api_key, message, logger):
    request = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(message).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CatchForm/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except Exception as exc:  # un e-mail raté ne doit jamais casser une soumission
        logger.warning("Échec de la notification e-mail : %s", exc)
