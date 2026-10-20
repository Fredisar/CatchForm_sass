"""Authentification : inscription, connexion, déconnexion."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import User

auth_bp = Blueprint("auth", __name__)


def _safe_next(target):
    """N'accepte qu'un chemin interne (« /dashboard »…) : évite les redirections ouvertes."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    # Les navigateurs traitent « \ » comme « / » et ignorent tabulations et retours
    # à la ligne : « /\evil.com » ou « /<TAB>/evil.com » mèneraient hors du site.
    if "\\" in target or any(ord(c) < 32 for c in target):
        return None
    return target


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Entre une adresse email valide.", "error")
        elif len(password) < 8:
            flash("Le mot de passe doit faire au moins 8 caractères.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Un compte existe déjà avec cet email.", "error")
        else:
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user, remember=True)
            flash("Bienvenue sur CatchForm 🎉 Crée ton premier formulaire.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(_safe_next(request.args.get("next")) or url_for("dashboard.index"))
        flash("Email ou mot de passe incorrect.", "error")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("public.index"))
