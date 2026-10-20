"""Pages publiques : landing, tarifs, sonde de santé."""
from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import text

from .extensions import db

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return render_template("landing.html")


@public_bp.route("/pricing")
def pricing():
    return render_template("pricing.html")


@public_bp.route("/healthz")
def healthz():
    """Utilisé par l'hébergeur pour vérifier que l'app et la base répondent."""
    db.session.execute(text("SELECT 1"))
    return {"status": "ok"}
