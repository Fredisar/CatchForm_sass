"""Endpoint public : reçoit les soumissions envoyées depuis n'importe quel site."""
import json

from flask import (Blueprint, current_app, jsonify, redirect, render_template,
                   request, url_for)

from . import notify
from .extensions import db
from .models import Form, Submission

ingest_bp = Blueprint("ingest", __name__)


@ingest_bp.after_request
def add_cors_headers(response):
    """Autorise les appels fetch() depuis un autre domaine (le site statique)."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _wants_json():
    return request.is_json or "application/json" in request.headers.get("Accept", "")


def _back_url():
    """Lien « retour » vers la page du formulaire, si le navigateur l'a fournie."""
    referrer = request.referrer or ""
    return referrer if referrer.startswith(("http://", "https://")) else None


def _notice(status, ok, title, message, form=None):
    return render_template(
        "notice.html", ok=ok, title=title, message=message, form=form, back_url=_back_url()
    ), status


def _error(status, code, title, message):
    if _wants_json():
        return jsonify({"ok": False, "error": code}), status
    return _notice(status, False, title, message)


def _success(form):
    if _wants_json():
        return jsonify({"ok": True})
    if form.redirect_url:
        return redirect(form.redirect_url, code=303)
    return _notice(200, True, "Merci !", "Ton message a bien été envoyé.", form=form)


def _read_payload():
    """Champs envoyés (form-data, urlencoded ou JSON), ou None si illisible."""
    if request.is_json:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else None
    # Les champs à valeurs multiples (cases à cocher) sont joints par des virgules.
    return {
        key: values[0] if len(values) == 1 else ", ".join(values)
        for key, values in request.form.lists()
    }


@ingest_bp.route("/f/<public_id>", methods=["GET"])
def info(public_id):
    """Page affichée si quelqu'un ouvre l'endpoint directement dans son navigateur."""
    if Form.query.filter_by(public_id=public_id).first() is None:
        return _error(404, "form_not_found", "Formulaire introuvable",
                      "Ce formulaire n'existe pas ou a été supprimé.")
    return _notice(200, True, "Endpoint actif ✓",
                   "Cette adresse reçoit les envois d'un formulaire HTML "
                   "(méthode POST). Elle ne s'ouvre pas directement.")


@ingest_bp.route("/f/<public_id>", methods=["POST"])
def submit(public_id):
    form = Form.query.filter_by(public_id=public_id).first()
    if form is None:
        return _error(404, "form_not_found", "Formulaire introuvable",
                      "Ce formulaire n'existe pas ou a été supprimé.")

    raw = _read_payload()
    if raw is None:
        return _error(400, "invalid_payload", "Envoi invalide",
                      "Le contenu envoyé n'a pas pu être lu.")

    # Anti-spam : le champ caché « _gotcha » n'est rempli que par les robots.
    if raw.get("_gotcha"):
        return _success(form)  # on fait mine d'accepter, sans rien enregistrer

    # « _subject » personnalise l'objet de l'e-mail ; les autres « _ » sont internes.
    subject = " ".join(str(raw.get("_subject") or "").split())[:150]
    payload = {k: v for k, v in raw.items() if not k.startswith("_")}
    if not payload:
        return _error(422, "empty_submission", "Formulaire vide",
                      "Aucun champ n'a été rempli.")

    owner = form.owner
    if not owner.is_pro:
        limit = current_app.config["FREE_PLAN_MONTHLY_LIMIT"]
        if owner.submissions_this_month() >= limit:
            return _error(402, "plan_limit_reached", "Limite atteinte",
                          "Ce formulaire ne peut plus recevoir de messages ce mois-ci. "
                          "Contacte directement le propriétaire du site.")

    db.session.add(Submission(
        form_id=form.id,
        data=json.dumps(payload, ensure_ascii=False),
        ip=request.remote_addr,
    ))
    db.session.commit()

    if form.notify:
        notify.send_submission_email(
            to=owner.email,
            form_name=form.name,
            fields=payload,
            subject=subject,
            dashboard_url=url_for("dashboard.form_detail", public_id=form.public_id,
                                  _external=True),
        )
    return _success(form)
