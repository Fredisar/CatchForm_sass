"""Recette HTTP de CatchForm contre un serveur réellement lancé (http://127.0.0.1:5000).

Usage : python recette_http.py
"""
import http.cookiejar
import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:5000"
results = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def make_client():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect())


def call(client, method, path, data=None, headers=None, json_body=None):
    url = path if path.startswith("http") else BASE + path
    body = None
    headers = dict(headers or {})
    if json_body is not None:
        body = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    elif data is not None:
        body = urllib.parse.urlencode(data, doseq=True).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        resp = client.open(req, timeout=15)
    except urllib.error.HTTPError as err:
        resp = err
    raw = resp.read()
    return resp.status, dict(resp.headers), raw


def text(raw):
    return raw.decode("utf-8", errors="replace")


def csrf(client, path):
    _, _, raw = call(client, "GET", path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', text(raw))
    assert match, f"jeton CSRF introuvable sur {path}"
    return match.group(1)


def check(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print(("OK   " if condition else "ÉCHEC") + f"  {label}" + (f"  ({detail})" if detail and not condition else ""))


def wait_for_server():
    for _ in range(40):
        try:
            urllib.request.urlopen(BASE + "/healthz", timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    sys.exit("Le serveur ne répond pas sur " + BASE)


def main():
    wait_for_server()
    owner = make_client()
    visitor = make_client()  # un site tiers : aucun cookie de session
    email = f"recette-{secrets.token_hex(3)}@example.com"

    # 1. Pages publiques
    status, headers, raw = call(owner, "GET", "/")
    check("Accueil (200, proposition de valeur)", status == 200 and "site statique" in text(raw))
    status, _, raw = call(owner, "GET", "/healthz")
    check("/healthz répond ok", status == 200 and json.loads(raw) == {"status": "ok"})
    status, _, raw = call(owner, "GET", "/pricing")
    check("Page Tarifs", status == 200 and "9 €" in text(raw))
    status, headers, _ = call(owner, "GET", "/static/style.css")
    check("Feuille de style servie", status == 200 and "css" in headers.get("Content-Type", ""))
    status, _, raw = call(owner, "GET", "/page-qui-n-existe-pas")
    check("Page 404 personnalisée", status == 404 and "n'existe pas" in text(raw).replace("&#39;", "'"))

    # 2. Inscription sans jeton CSRF : refusée
    status, _, _ = call(owner, "POST", "/register", data={"email": email, "password": "motdepasse123"})
    check("Inscription sans jeton CSRF refusée (400)", status == 400)

    # 3. Inscription normale
    token = csrf(owner, "/register")
    status, headers, _ = call(owner, "POST", "/register",
                              data={"csrf_token": token, "email": email, "password": "motdepasse123"})
    check("Inscription -> redirection tableau de bord", status == 302 and headers.get("Location", "").endswith("/dashboard"))
    status, _, raw = call(owner, "GET", "/dashboard")
    check("Tableau de bord affiché avec jauge 0/100", status == 200 and "Mes formulaires" in text(raw) and "0 / 100" in text(raw))

    # 4. Création d'un formulaire
    token = csrf(owner, "/dashboard")
    status, headers, _ = call(owner, "POST", "/forms",
                              data={"csrf_token": token, "name": "Contact recette", "redirect_url": ""})
    location = headers.get("Location", "")
    public_id = location.rsplit("/", 1)[-1]
    check("Création du formulaire", status == 302 and "/forms/" in location)
    status, _, raw = call(owner, "GET", f"/forms/{public_id}")
    match = re.search(r'<code id="endpoint">([^<]+)</code>', text(raw))
    endpoint = match.group(1).strip() if match else ""
    check("Endpoint affiché", endpoint == f"{BASE}/f/{public_id}", endpoint)

    # 5. Envoi depuis un site tiers (comme exemple/contact.html)
    origin = {"Origin": "https://monsite.example", "Referer": "https://monsite.example/contact"}
    status, headers, raw = call(visitor, "POST", endpoint, headers=origin, data={
        "nom": "Zoé Martin", "email": "zoe@example.com", "message": "Bonjour, un devis ?",
        "interets": ["design", "seo"], "_subject": "Demande de devis", "_gotcha": "",
    })
    body = text(raw)
    check("Envoi HTML depuis un site tiers -> page Merci", status == 200 and "Merci" in body)
    check("Lien « Retour au site » vers le site d'origine", "https://monsite.example/contact" in body)
    check("Mention « Propulsé par CatchForm » (plan gratuit)", "Propulsé par" in body)
    check("En-tête CORS présent", headers.get("Access-Control-Allow-Origin") == "*")

    status, _, raw = call(visitor, "POST", endpoint, headers={"Accept": "application/json", **origin},
                          json_body={"email": "api@example.com", "message": "Envoi fetch()"})
    check("Envoi JSON (fetch) -> {\"ok\": true}", status == 200 and json.loads(raw) == {"ok": True})

    status, headers, _ = call(visitor, "OPTIONS", endpoint, headers={
        **origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    check("Requête préliminaire CORS (OPTIONS)", status == 200 and "POST" in headers.get("Access-Control-Allow-Methods", ""))

    status, _, raw = call(visitor, "POST", endpoint, headers=origin,
                          data={"email": "bot@spam.example", "_gotcha": "http://spam.example"})
    check("Robot (champ piège) : faux succès", status == 200 and "Merci" in text(raw))

    status, _, raw = call(visitor, "POST", endpoint, headers={"Accept": "application/json"}, data={"_gotcha": ""})
    check("Formulaire vide refusé (422)", status == 422 and json.loads(raw)["error"] == "empty_submission")

    status, _, raw = call(visitor, "POST", f"{BASE}/f/inexistant", headers={"Accept": "application/json"}, data={"a": "1"})
    check("Formulaire inconnu (404)", status == 404)

    status, _, raw = call(visitor, "GET", endpoint)
    check("Endpoint ouvert dans un navigateur -> page d'information", status == 200 and "Endpoint actif" in text(raw))

    # 6. Consultation par le client
    status, _, raw = call(owner, "GET", f"/forms/{public_id}")
    page = text(raw)
    check("2 soumissions enregistrées (le robot est ignoré)", "2 soumissions reçues" in page)
    check("Contenu affiché (accents, cases multiples)", "Zoé Martin" in page and "design, seo" in page)
    check("Champ piège et _subject non enregistrés", "bot@spam.example" not in page and "Demande de devis" not in page)

    status, headers, raw = call(owner, "GET", f"/forms/{public_id}/export.csv")
    csv_text = raw.decode("utf-8")
    check("Export CSV avec BOM UTF-8", status == 200 and csv_text.startswith(chr(0xFEFF)))
    check("Colonnes CSV", csv_text.lstrip(chr(0xFEFF)).splitlines()[0] == "date_utc,email,message,nom,interets",
          csv_text.lstrip(chr(0xFEFF)).splitlines()[0])

    # 7. Redirection configurée
    token = csrf(owner, f"/forms/{public_id}")
    call(owner, "POST", f"/forms/{public_id}/settings", data={
        "csrf_token": token, "name": "Contact recette", "redirect_url": "https://monsite.example/merci", "notify": "on"})
    status, headers, _ = call(visitor, "POST", endpoint, data={"message": "avec redirection"})
    check("Redirection 303 vers la page configurée", status == 303 and headers.get("Location") == "https://monsite.example/merci")

    # 8. Isolation entre comptes
    intruder = make_client()
    token = csrf(intruder, "/register")
    call(intruder, "POST", "/register", data={
        "csrf_token": token, "email": f"intrus-{secrets.token_hex(3)}@example.com", "password": "motdepasse123"})
    status, _, _ = call(intruder, "GET", f"/forms/{public_id}")
    check("Un autre compte ne voit pas le formulaire (404)", status == 404)
    status, _, _ = call(intruder, "GET", f"/forms/{public_id}/export.csv")
    check("Un autre compte ne peut pas exporter (404)", status == 404)

    # 9. Déconnexion
    status, headers, _ = call(owner, "GET", "/logout")
    status, headers, _ = call(owner, "GET", "/dashboard")
    check("Après déconnexion, le tableau de bord exige une connexion", status == 302 and "/login" in headers.get("Location", ""))

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} vérifications réussies")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
