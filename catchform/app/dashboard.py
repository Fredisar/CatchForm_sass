"""Tableau de bord : formulaires, soumissions, paramètres, export CSV."""
import csv
import io

from flask import (Blueprint, Response, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required
from sqlalchemy import select

from .extensions import db
from .models import Form, Submission
from .utils import as_text

dashboard_bp = Blueprint("dashboard", __name__)

# Préfixes qu'Excel interprète comme une formule à l'ouverture d'un CSV.
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", chr(9), chr(13))

# Marque d'ordre des octets : Excel détecte l'UTF-8 et affiche bien les accents.
UTF8_BOM = chr(0xFEFF)


def _get_owned_form(public_id):
    """Formulaire de l'utilisateur connecté, sinon 404 (on ne révèle pas son existence)."""
    return Form.query.filter_by(
        public_id=public_id, user_id=current_user.id
    ).first_or_404()


def _clean_redirect_url(raw):
    """Retourne (url_ou_None, valide). Seules les URLs http(s) sont acceptées."""
    url = (raw or "").strip()
    if not url:
        return None, True
    if url.startswith(("http://", "https://")) and len(url) <= 500:
        return url, True
    return None, False


def _csv_cell(value):
    """Neutralise les formules (=, +, -, @) envoyées par des inconnus."""
    text = as_text(value)
    return "'" + text if text.startswith(CSV_FORMULA_PREFIXES) else text


@dashboard_bp.route("/dashboard")
@login_required
def index():
    forms = (
        Form.query.filter_by(user_id=current_user.id)
        .order_by(Form.created_at.desc())
        .all()
    )
    return render_template(
        "dashboard.html", forms=forms, usage=current_user.submissions_this_month()
    )


@dashboard_bp.route("/forms", methods=["POST"])
@login_required
def create_form():
    name = request.form.get("name", "").strip()[:120] or "Formulaire sans nom"
    redirect_url, valid = _clean_redirect_url(request.form.get("redirect_url"))
    if not valid:
        flash("L'URL de redirection doit commencer par http:// ou https://", "error")
        return redirect(url_for("dashboard.index"))
    form = Form(name=name, redirect_url=redirect_url, user_id=current_user.id)
    db.session.add(form)
    db.session.commit()
    flash("Formulaire créé — copie ton endpoint ci-dessous 👇", "success")
    return redirect(url_for("dashboard.form_detail", public_id=form.public_id))


@dashboard_bp.route("/forms/<public_id>")
@login_required
def form_detail(public_id):
    form = _get_owned_form(public_id)
    submissions = db.paginate(
        select(Submission).filter_by(form_id=form.id).order_by(Submission.id.desc()),
        page=request.args.get("page", 1, type=int),
        per_page=current_app.config["SUBMISSIONS_PER_PAGE"],
        error_out=False,
    )
    limit = current_app.config["FREE_PLAN_MONTHLY_LIMIT"]
    limit_reached = not current_user.is_pro and current_user.submissions_this_month() >= limit
    return render_template(
        "form_detail.html",
        form=form,
        submissions=submissions,
        endpoint=url_for("ingest.submit", public_id=form.public_id, _external=True),
        limit_reached=limit_reached,
        email_enabled=bool(current_app.config["RESEND_API_KEY"]),
    )


@dashboard_bp.route("/forms/<public_id>/settings", methods=["POST"])
@login_required
def update_form(public_id):
    form = _get_owned_form(public_id)
    redirect_url, valid = _clean_redirect_url(request.form.get("redirect_url"))
    if not valid:
        flash("L'URL de redirection doit commencer par http:// ou https://", "error")
    else:
        form.name = request.form.get("name", "").strip()[:120] or form.name
        form.redirect_url = redirect_url
        form.notify = request.form.get("notify") == "on"
        db.session.commit()
        flash("Paramètres enregistrés.", "success")
    return redirect(url_for("dashboard.form_detail", public_id=form.public_id))


@dashboard_bp.route("/forms/<public_id>/delete", methods=["POST"])
@login_required
def delete_form(public_id):
    form = _get_owned_form(public_id)
    db.session.delete(form)
    db.session.commit()
    flash("Formulaire supprimé.", "success")
    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/submissions/<int:submission_id>/delete", methods=["POST"])
@login_required
def delete_submission(submission_id):
    sub = db.session.scalar(
        select(Submission)
        .join(Form)
        .where(Submission.id == submission_id, Form.user_id == current_user.id)
    )
    if sub is None:
        abort(404)
    public_id = sub.form.public_id
    db.session.delete(sub)
    db.session.commit()
    return redirect(url_for("dashboard.form_detail", public_id=public_id))


@dashboard_bp.route("/forms/<public_id>/export.csv")
@login_required
def export_csv(public_id):
    form = _get_owned_form(public_id)
    rows = [(sub.created_at, sub.fields) for sub in form.submissions]

    # Les colonnes = union ordonnée de toutes les clés rencontrées.
    columns = []
    for _, fields in rows:
        for key in fields:
            if key not in columns:
                columns.append(key)

    buffer = io.StringIO()
    buffer.write(UTF8_BOM)
    writer = csv.writer(buffer)
    writer.writerow(["date_utc"] + [_csv_cell(c) for c in columns])
    for created_at, fields in rows:
        writer.writerow(
            [created_at.strftime("%Y-%m-%d %H:%M:%S")]
            + [_csv_cell(fields.get(c)) for c in columns]
        )

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=catchform-{form.public_id}.csv"
        },
    )
