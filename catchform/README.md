# ◆ CatchForm

**Le backend de formulaires pour sites statiques.** Tes utilisateurs collent une URL dans l'attribut `action` de leur `<form>`. CatchForm reçoit les soumissions, bloque le spam, envoie un e-mail et range tout dans un tableau de bord.

> 🚀 **Mise en ligne : voir [DEPLOIEMENT.md](DEPLOIEMENT.md)** (≈ 15 min, 0 € pour démarrer).

---

## 💡 L'idée

**Le problème.** Une grande partie des sites web sont statiques : HTML pur, GitHub Pages, Hugo, Jekyll, Astro, Netlify… Ils sont rapides et gratuits à héberger. Mais il faut un serveur pour recevoir les données d'un formulaire de contact. Un freelance qui livre un site vitrine ne veut pas monter (et maintenir) un backend juste pour ça.

**La solution.** CatchForm donne à chaque formulaire une URL d'endpoint. On la colle dans `action="…"` et c'est terminé, sans aucune ligne de code serveur.

**Cible.** Freelances et agences web, développeurs de sites statiques, makers no-code.

**Pourquoi ça peut marcher :**
- **Marché prouvé.** Formspree, Basin, Getform et Web3Forms vivent de ce modèle.
- **Produit facile à vendre.** On le comprend en 30 secondes et on l'adopte en 3 minutes.
- **Revenu récurrent.** Chaque client supplémentaire ne coûte presque rien à servir.
- **Acquisition virale.** La mention « Propulsé par CatchForm » apparaît sur chaque page de remerciement du plan gratuit.
- **Différenciation.** Interface en français, données hébergées dans l'UE (RGPD), prix plus bas que les leaders.

### Modèle économique

| Plan | Prix | Contenu |
|---|---|---|
| Gratuit | 0 € | 100 soumissions/mois, formulaires illimités, e-mails, anti-spam, export CSV |
| Pro | 9 €/mois | Soumissions illimitées, page « merci » sans la mention CatchForm, support prioritaire |

Deux clients Pro suffisent à payer un hébergement sans mise en veille. Cent clients Pro représentent environ 900 €/mois de revenu récurrent.

### Trouver les premiers clients
- Écrire des tutoriels SEO : « formulaire de contact Hugo / Jekyll / GitHub Pages / Astro sans backend ».
- Publier sur Reddit (r/webdev, r/SideProject), Indie Hackers, Product Hunt et dans les communautés de devs francophones.
- Démarcher les freelances et agences web, qui livrent des dizaines de sites vitrines par an.

---

## ✅ Fonctionnalités (MVP)

- **Comptes** : inscription, connexion, session mémorisée 30 jours.
- **Formulaires illimités** : chacun a un endpoint unique et non devinable (`/f/<id>`).
- **Réception** :
  - envoi HTML classique (form-data / urlencoded) **ou** JSON via `fetch()` (CORS ouvert) ;
  - les cases à cocher multiples sont regroupées.
- **Anti-spam** par champ piège `_gotcha` : les robots sont ignorés sans le savoir.
- **Notifications e-mail** (API Resend) :
  - le bouton « Répondre » écrit directement au visiteur ;
  - l'objet est personnalisable avec `_subject`.
- **Après l'envoi** : redirection vers la page de ton choix, sinon page « Merci » propre.
- **Tableau de bord** : soumissions paginées, suppression, paramètres par formulaire.
- **Export CSV** compatible Excel : accents corrects, injection de formules neutralisée.
- **Plans Gratuit / Pro** avec limite mensuelle et jauge d'utilisation.
- **Sécurité** :
  - CSRF, cookies `Secure` / `HttpOnly` / `SameSite`, mots de passe hachés ;
  - anti-redirection ouverte, isolation stricte des données entre comptes, taille des requêtes limitée.
- **Tests automatisés** de tous les parcours (`tests/test_app.py`).

## 🧱 Stack

Python 3.10+ · Flask 3 · Flask-SQLAlchemy · Flask-Login · Flask-WTF · SQLite (local) / PostgreSQL (production) · Gunicorn · Resend · Render.

---

## 🖥️ Lancer en local (Windows / PowerShell)

```powershell
cd C:\Users\toshiba\Flask\catchform
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python wsgi.py
```

Ouvre ensuite **http://127.0.0.1:5000**. Aucune configuration n'est nécessaire : la base SQLite se crée toute seule dans `instance/catchform.db`.

### Tester le parcours complet
1. Crée un compte, puis un formulaire, et copie son endpoint.
2. Ouvre `exemple/contact.html` dans un éditeur. Dans l'attribut `action`, remplace `REMPLACE-MOI` par l'identifiant de ton formulaire.
3. Double-clique sur ce fichier pour l'ouvrir dans le navigateur, remplis-le et envoie.
4. La soumission apparaît dans ton tableau de bord 🎉

### Lancer les tests
```powershell
.venv\Scripts\python -m pytest
```

### Passer un compte en Pro (en local)
```powershell
.venv\Scripts\flask --app wsgi set-plan email@exemple.com pro
```

---

## ⚙️ Configuration (variables d'environnement)

| Variable | Rôle | Par défaut |
|---|---|---|
| `SECRET_KEY` | Signe les sessions. **Obligatoire en production.** | valeur de dev |
| `DATABASE_URL` | URL PostgreSQL (`postgres://…` ou `postgresql://…`) | SQLite local |
| `SESSION_COOKIE_SECURE` | `1` quand le site est servi en HTTPS | `0` |
| `RESEND_API_KEY` | Active les notifications e-mail | vide (désactivées) |
| `MAIL_FROM` | Expéditeur des e-mails | `CatchForm <onboarding@resend.dev>` |
| `CONTACT_EMAIL` | Destinataire du bouton « Passer Pro » | `contact@example.com` |
| `FREE_PLAN_MONTHLY_LIMIT` | Soumissions par mois du plan gratuit | `100` |

---

## 🔌 Intégration (ce que tes utilisateurs collent sur leur site)

```html
<form method="POST" action="https://ton-app.onrender.com/f/ID_DU_FORMULAIRE">
  <input name="email" type="email" required>
  <textarea name="message"></textarea>
  <input type="hidden" name="_subject" value="Nouveau message du site">
  <input type="text" name="_gotcha" style="display:none">
  <button>Envoyer</button>
</form>
```

| Champ spécial | Effet |
|---|---|
| `_gotcha` | Piège à robots : si ce champ caché est rempli, l'envoi est ignoré |
| `_subject` | Objet de l'e-mail de notification |
| `email` | Devient l'adresse de réponse de l'e-mail de notification |

En JavaScript, `fetch(endpoint, { method: "POST", body: new FormData(form), headers: { Accept: "application/json" } })` renvoie `{"ok": true}`.

---

## 🗂️ Structure

```
catchform/
├── app/
│   ├── __init__.py       # app factory, pages d'erreur, commande « set-plan »
│   ├── models.py         # User, Form, Submission
│   ├── auth.py           # inscription / connexion
│   ├── dashboard.py      # tableau de bord, paramètres, export CSV
│   ├── ingest.py         # endpoint public /f/<id> : le cœur du produit
│   ├── notify.py         # e-mails via Resend
│   ├── public.py         # accueil, tarifs, /healthz
│   ├── templates/        # pages HTML (Jinja)
│   └── static/style.css
├── tests/test_app.py     # tests automatisés
├── exemple/contact.html  # site statique de démonstration
├── config.py             # configuration par variables d'environnement
├── wsgi.py               # point d'entrée (local + Gunicorn)
├── render.yaml           # déploiement Render en un clic
├── Procfile              # Railway / Koyeb / Heroku
└── requirements.txt
```

## 🛣️ Feuille de route

1. **Paiement Stripe** (Checkout + webhooks) pour automatiser le passage en Pro.
2. Réinitialisation du mot de passe par e-mail.
3. Limitation de débit (Flask-Limiter) sur l'endpoint public.
4. ⚠️ **Migrations de base (Flask-Migrate) avant toute modification des modèles.** `db.create_all()` crée les tables manquantes mais ne modifie jamais une table existante.
5. Suppression de compte et export des données (RGPD).
6. Intégrations : webhooks, Slack, Google Sheets, Zapier.
7. Pièces jointes (CV, fichiers).
