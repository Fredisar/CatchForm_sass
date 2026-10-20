"""Tests de bout en bout de CatchForm (client de test Flask, SQLite en mémoire)."""
from datetime import timedelta

import pytest

from app import create_app, notify
from app.auth import _safe_next
from app.extensions import db
from app.models import Form, Submission, User, month_start
from config import Config


class ConfigForTests(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    FREE_PLAN_MONTHLY_LIMIT = 3
    SUBMISSIONS_PER_PAGE = 2
    RESEND_API_KEY = ""


@pytest.fixture
def app():
    return create_app(ConfigForTests)


@pytest.fixture
def client(app):
    return app.test_client()


def signup(client, email="alice@example.com", password="motdepasse123"):
    return client.post("/register", data={"email": email, "password": password})


def new_form(client, name="Contact", redirect_url=""):
    resp = client.post("/forms", data={"name": name, "redirect_url": redirect_url})
    assert resp.status_code == 302
    return resp.headers["Location"].rsplit("/", 1)[-1]


# --- Pages publiques & authentification ------------------------------------

def test_public_pages(client):
    assert "site statique" in client.get("/").get_data(as_text=True)
    assert client.get("/pricing").status_code == 200
    assert client.get("/healthz").get_json() == {"status": "ok"}
    assert client.get("/page-inexistante").status_code == 404


def test_register_login_logout(client):
    resp = signup(client)
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")
    assert "alice@example.com" in client.get("/dashboard").get_data(as_text=True)

    client.get("/logout")
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login?next=%2Fdashboard" in resp.headers["Location"]

    resp = client.post("/login", data={"email": "alice@example.com", "password": "mauvais"})
    assert "incorrect" in resp.get_data(as_text=True)

    resp = client.post("/login?next=/forms/xyz",
                       data={"email": " ALICE@example.com ", "password": "motdepasse123"})
    assert resp.headers["Location"] == "/forms/xyz"


def test_register_validation(client, app):
    resp = client.post("/register", data={"email": "bob@example.com", "password": "court"})
    assert "doit faire au moins 8 caractères" in resp.get_data(as_text=True)

    signup(client, "bob@example.com")
    client.get("/logout")
    resp = signup(client, "BOB@example.com")
    assert "existe déjà" in resp.get_data(as_text=True)
    with app.app_context():
        assert User.query.count() == 1


@pytest.mark.parametrize("target, expected", [
    ("/dashboard", "/dashboard"),
    ("/forms/abc?page=2", "/forms/abc?page=2"),
    ("https://evil.com", None),
    ("//evil.com", None),
    ("/\\evil.com", None),
    ("/\t/evil.com", None),
    ("", None),
    (None, None),
])
def test_safe_next_blocks_open_redirects(target, expected):
    assert _safe_next(target) == expected


# --- Endpoint public d'ingestion -------------------------------------------

def test_submission_flow(client, app):
    signup(client)
    public_id = new_form(client)

    resp = client.post(f"/f/{public_id}", data={
        "email": "visiteur@example.com",
        "message": "Bonjour !",
        "interets": ["design", "seo"],
        "_gotcha": "",
        "_subject": "Hello",
    })
    assert resp.status_code == 200
    assert "Merci" in resp.get_data(as_text=True)

    with app.app_context():
        assert Submission.query.one().fields == {
            "email": "visiteur@example.com",
            "message": "Bonjour !",
            "interets": "design, seo",
        }

    page = client.get(f"/forms/{public_id}").get_data(as_text=True)
    assert "visiteur@example.com" in page and "Bonjour !" in page


def test_json_submission_and_cors(client):
    signup(client)
    public_id = new_form(client)

    resp = client.post(f"/f/{public_id}", json={"email": "a@b.co", "details": {"x": 1}})
    assert resp.get_json() == {"ok": True}
    assert resp.headers["Access-Control-Allow-Origin"] == "*"

    preflight = client.options(f"/f/{public_id}", headers={
        "Origin": "https://monsite.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert preflight.status_code == 200
    assert preflight.headers["Access-Control-Allow-Origin"] == "*"
    assert "Content-Type" in preflight.headers["Access-Control-Allow-Headers"]


def test_honeypot_silently_drops_spam(client, app):
    signup(client)
    public_id = new_form(client)
    resp = client.post(f"/f/{public_id}", data={"email": "bot@spam.io", "_gotcha": "http://spam"})
    assert resp.status_code == 200
    with app.app_context():
        assert Submission.query.count() == 0


def test_rejects_empty_invalid_and_unknown(client):
    signup(client)
    public_id = new_form(client)
    assert client.post(f"/f/{public_id}", data={"_gotcha": ""}).status_code == 422
    assert client.post(f"/f/{public_id}", json=["pas", "un", "objet"]).status_code == 400
    resp = client.post("/f/inconnu", json={"a": 1})
    assert resp.status_code == 404 and resp.get_json()["error"] == "form_not_found"
    assert client.get(f"/f/{public_id}").status_code == 200  # page d'info


def test_redirect_after_submission(client):
    signup(client)
    public_id = new_form(client, redirect_url="https://monsite.com/merci")
    resp = client.post(f"/f/{public_id}", data={"message": "ok"})
    assert resp.status_code == 303
    assert resp.headers["Location"] == "https://monsite.com/merci"


def test_invalid_redirect_url_is_rejected(client, app):
    signup(client)
    resp = client.post("/forms", data={"name": "X", "redirect_url": "javascript:alert(1)"})
    assert resp.headers["Location"].endswith("/dashboard")
    with app.app_context():
        assert Form.query.count() == 0


def test_free_plan_monthly_limit(client, app):
    signup(client)
    public_id = new_form(client)
    for i in range(3):
        assert client.post(f"/f/{public_id}", data={"n": str(i)}).status_code == 200
    resp = client.post(f"/f/{public_id}", data={"n": "4"}, headers={"Accept": "application/json"})
    assert resp.status_code == 402
    assert resp.get_json()["error"] == "plan_limit_reached"
    assert "Limite atteinte" in client.get("/dashboard").get_data(as_text=True)

    # Les envois du mois précédent ne comptent pas.
    with app.app_context():
        Submission.query.first().created_at = month_start() - timedelta(days=1)
        db.session.commit()
    assert client.post(f"/f/{public_id}", data={"n": "5"}).status_code == 200

    # Un client Pro n'a pas de limite.
    with app.app_context():
        User.query.one().plan = "pro"
        db.session.commit()
    for i in range(5):
        assert client.post(f"/f/{public_id}", data={"n": str(i)}).status_code == 200


def test_pro_thank_you_page_has_no_branding(client, app):
    signup(client)
    public_id = new_form(client)
    assert "Propulsé par" in client.post(f"/f/{public_id}", data={"a": "1"}).get_data(as_text=True)
    with app.app_context():
        User.query.one().plan = "pro"
        db.session.commit()
    assert "Propulsé par" not in client.post(f"/f/{public_id}", data={"a": "2"}).get_data(as_text=True)


def test_email_notification(client, app, monkeypatch):
    sent = []

    class ImmediateThread:
        def __init__(self, target, args=(), daemon=None):
            self.target, self.args = target, args

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr(notify.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(notify, "_post", lambda api_key, message, logger: sent.append(message))
    app.config["RESEND_API_KEY"] = "re_test"

    signup(client)
    public_id = new_form(client)
    client.post(f"/f/{public_id}", data={
        "email": "visiteur@example.com",
        "message": "<script>alert(1)</script>",
        "_subject": "Devis\nurgent",
    })

    assert len(sent) == 1
    message = sent[0]
    assert message["to"] == ["alice@example.com"]
    assert message["subject"] == "Devis urgent"
    assert message["reply_to"] == "visiteur@example.com"
    assert "&lt;script&gt;" in message["html"] and "<script>" not in message["html"]

    # Notifications désactivées dans les paramètres : plus d'e-mail.
    client.post(f"/forms/{public_id}/settings", data={"name": "Contact"})
    client.post(f"/f/{public_id}", data={"message": "silence"})
    assert len(sent) == 1


# --- Tableau de bord ---------------------------------------------------------

def test_users_cannot_touch_other_users_forms(client, app):
    signup(client, "alice@example.com")
    public_id = new_form(client)
    client.post(f"/f/{public_id}", data={"secret": "42"})
    client.get("/logout")

    signup(client, "mallory@example.com")
    assert client.get(f"/forms/{public_id}").status_code == 404
    assert client.get(f"/forms/{public_id}/export.csv").status_code == 404
    assert client.post(f"/forms/{public_id}/delete").status_code == 404
    with app.app_context():
        sub_id = Submission.query.one().id
    assert client.post(f"/submissions/{sub_id}/delete").status_code == 404
    with app.app_context():
        assert Form.query.count() == 1 and Submission.query.count() == 1


def test_update_settings(client, app):
    signup(client)
    public_id = new_form(client)
    client.post(f"/forms/{public_id}/settings",
                data={"name": "Devis", "redirect_url": "https://site.fr/ok"})
    with app.app_context():
        form = Form.query.one()
        assert (form.name, form.redirect_url, form.notify) == ("Devis", "https://site.fr/ok", False)


def test_delete_submission_and_form(client, app):
    signup(client)
    public_id = new_form(client)
    client.post(f"/f/{public_id}", data={"a": "1"})
    with app.app_context():
        sub_id = Submission.query.one().id
    assert client.post(f"/submissions/{sub_id}/delete").status_code == 302
    client.post(f"/f/{public_id}", data={"a": "2"})
    assert client.post(f"/forms/{public_id}/delete").status_code == 302
    with app.app_context():
        assert Form.query.count() == 0 and Submission.query.count() == 0


def test_pagination(client):
    signup(client)
    public_id = new_form(client)
    for i in range(3):
        client.post(f"/f/{public_id}", data={"n": f"valeur-{i}"})
    page1 = client.get(f"/forms/{public_id}").get_data(as_text=True)
    page2 = client.get(f"/forms/{public_id}?page=2").get_data(as_text=True)
    assert "Page 1 / 2" in page1 and "valeur-2" in page1 and "valeur-0" not in page1
    assert "valeur-0" in page2


def test_csv_export_is_excel_safe(client):
    signup(client)
    public_id = new_form(client)
    client.post(f"/f/{public_id}", data={"nom": "Zoé", "formule": '=HYPERLINK("http://x")'})

    resp = client.get(f"/forms/{public_id}/export.csv")
    assert resp.mimetype == "text/csv"
    body = resp.data.decode("utf-8")
    assert body.startswith(chr(0xFEFF))
    header, row = body.lstrip(chr(0xFEFF)).splitlines()[:2]
    assert header == "date_utc,nom,formule"
    assert "Zoé" in row and "'=HYPERLINK" in row


# --- Sécurité & administration ----------------------------------------------

def test_csrf_protects_dashboard_but_not_public_endpoint():
    app = create_app(type("CsrfConfig", (ConfigForTests,), {"WTF_CSRF_ENABLED": True}))
    client = app.test_client()
    resp = client.post("/register", data={"email": "x@y.fr", "password": "motdepasse123"})
    assert resp.status_code == 400

    with app.app_context():
        user = User(email="owner@example.com")
        user.set_password("motdepasse123")
        form = Form(name="Contact", owner=user)
        db.session.add(form)
        db.session.commit()
        public_id = form.public_id
    assert client.post(f"/f/{public_id}", data={"message": "salut"}).status_code == 200


def test_cli_set_plan(client, app):
    signup(client)
    result = app.test_cli_runner().invoke(args=["set-plan", "alice@example.com", "pro"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert User.query.one().plan == "pro"
