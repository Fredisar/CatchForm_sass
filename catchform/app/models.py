"""Modèles de données : User, Form, Submission."""
import json
import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def utcnow():
    """Horodatage UTC « naïf », stocké tel quel en base."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def month_start(now=None):
    now = now or utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _public_id():
    """Identifiant public court et non devinable pour l'URL d'endpoint."""
    return secrets.token_urlsafe(8)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    plan = db.Column(db.String(20), nullable=False, default="free")  # "free" | "pro"
    created_at = db.Column(db.DateTime, default=utcnow)

    forms = db.relationship(
        "Form", backref="owner", cascade="all, delete-orphan", lazy=True
    )

    @property
    def is_pro(self):
        return self.plan == "pro"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def submissions_this_month(self):
        """Soumissions reçues depuis le 1er du mois, tous formulaires confondus."""
        return db.session.scalar(
            select(func.count(Submission.id))
            .select_from(Submission)
            .join(Form)
            .where(Form.user_id == self.id, Submission.created_at >= month_start())
        )


class Form(db.Model):
    __tablename__ = "forms"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(
        db.String(16), unique=True, index=True, nullable=False, default=_public_id
    )
    name = db.Column(db.String(120), nullable=False)
    redirect_url = db.Column(db.String(500))  # redirection optionnelle après envoi
    notify = db.Column(db.Boolean, nullable=False, default=True)  # e-mail à chaque envoi
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    submissions = db.relationship(
        "Submission",
        backref="form",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="Submission.id.desc()",
    )

    @property
    def submission_count(self):
        return db.session.scalar(
            select(func.count(Submission.id)).where(Submission.form_id == self.id)
        )


class Submission(db.Model):
    __tablename__ = "submissions"

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey("forms.id"), nullable=False, index=True)
    data = db.Column(db.Text, nullable=False, default="{}")  # payload JSON
    ip = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=utcnow, index=True)

    @property
    def fields(self):
        """Retourne le payload décodé sous forme de dict."""
        try:
            value = json.loads(self.data or "{}")
        except (ValueError, TypeError):
            return {}
        return value if isinstance(value, dict) else {}
