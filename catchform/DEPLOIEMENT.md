# 🚀 Déployer CatchForm en production

Ce guide met CatchForm en ligne sur **Render** : HTTPS, base PostgreSQL, serveurs à **Francfort** (UE). Compte environ **15 minutes**, pour **0 €** au départ.

Tout ce qui relève du code est déjà prêt :
- `render.yaml` crée l'app et la base en un clic ;
- Gunicorn sert l'app, `/healthz` sert de sonde de santé ;
- les URLs générées restent en HTTPS derrière le proxy ;
- les cookies sont sécurisés.

Il ne te reste que les étapes qui demandent **tes comptes**.

---

## Étape 0 — Prérequis (une seule fois)

- Un compte **GitHub** : https://github.com/signup
- Un compte **Render** (le plus simple : « Sign up with GitHub ») : https://dashboard.render.com/register
- **Git** installé sur ton PC : https://git-scm.com/download/win

## Étape 1 — Mettre le code sur GitHub

1. Crée un dépôt **vide** sur https://github.com/new :
   - nom : `catchform` ;
   - visibilité : **Private** (recommandé) ;
   - ⚠️ ne coche **pas** « Add a README » : le dépôt doit être vide.
2. Dans PowerShell, remplace `TON-PSEUDO` par ton pseudo GitHub :

```powershell
cd C:\Users\toshiba\Flask\catchform
git init
git add .
git commit -m "CatchForm MVP"
git branch -M main
git remote add origin https://github.com/TON-PSEUDO/catchform.git
git push -u origin main
```

> Si `git commit` répond « Please tell me who you are », configure ton identité une fois, puis relance le commit :
> ```powershell
> git config --global user.name "Ton Nom"
> git config --global user.email "ton@email.com"
> ```

## Étape 2 — Créer l'app sur Render (Blueprint)

1. Sur https://dashboard.render.com, clique **New +** → **Blueprint**.
2. Autorise l'accès à GitHub si on te le demande, puis choisis le dépôt `catchform`.
3. Render lit `render.yaml` et annonce ce qu'il va créer :
   - un **Web Service** `catchform` (Python, plan Free, Frankfurt) ;
   - une base **PostgreSQL** `catchform-db` (plan Free, Frankfurt).
4. Donne un nom au Blueprint (par exemple `catchform`) et valide (**Apply** / **Deploy Blueprint**).
5. Attends que le service passe au statut **Live** (3 à 6 minutes).

L'adresse de ton app s'affiche en haut de la page du service, sous la forme `https://catchform-xxxx.onrender.com`.

> Rien à copier-coller : `SECRET_KEY` est générée automatiquement et `DATABASE_URL` pointe déjà vers la base.

## Étape 3 — Vérifier que tout marche

1. Ouvre `https://TON-APP.onrender.com/healthz` : la page doit afficher `{"status":"ok"}`.
2. Sur la page d'accueil, crée un compte puis un formulaire.
3. Copie l'endpoint (il commence par `https://`).
4. Dans `exemple/contact.html`, remplace l'URL de l'attribut `action` par cet endpoint. Ouvre le fichier dans le navigateur et envoie un message.
5. Le message apparaît dans le tableau de bord ✅

## Étape 4 — Activer les notifications e-mail (recommandé)

1. Crée un compte sur https://resend.com, puis **API Keys** → **Create API Key** (accès « Sending access »).
2. Sur Render, ouvre le service `catchform` → **Environment** → **Add Environment Variable**, puis ajoute `RESEND_API_KEY` = ta clé (`re_…`).
3. Clique **Save Changes** : Render redéploie tout seul.

> ⚠️ **Sans domaine vérifié, Resend n'envoie qu'à l'adresse de ton propre compte Resend.** C'est parfait pour tester. Pour de vrais clients :
> 1. dans Resend → **Domains**, ajoute ton domaine et crée les enregistrements DNS indiqués ;
> 2. sur Render, ajoute `MAIL_FROM` = `CatchForm <notifications@ton-domaine.fr>`.

## Étape 5 — Bouton « Passer Pro »

Ajoute la variable `CONTACT_EMAIL` avec ton adresse e-mail. Le bouton « Passer Pro » de la page Tarifs t'enverra alors les demandes.

## Étape 6 — Passer un client en Pro (en attendant Stripe)

Une fois le client payé (virement, PayPal, lien de paiement Stripe…) :

1. Sur Render, ouvre la base `catchform-db` → **Connect**, puis copie l'**External Database URL**.
2. Dans PowerShell, sur ton PC (avec le `.venv` créé lors de l'installation locale, voir le README) :

```powershell
cd C:\Users\toshiba\Flask\catchform
$env:DATABASE_URL = "COLLE-ICI-L-EXTERNAL-DATABASE-URL"
.venv\Scripts\flask --app wsgi set-plan client@exemple.com pro
Remove-Item Env:DATABASE_URL
```

## Étape 7 — Ton propre nom de domaine (optionnel)

1. Sur Render, ouvre le service `catchform` → **Settings** → **Custom Domains**, puis ajoute par exemple `app.ton-domaine.fr`.
2. Chez ton registrar (OVH, Gandi, Cloudflare…), crée l'enregistrement **CNAME** indiqué par Render.
3. Le certificat HTTPS se génère automatiquement. Quand tu passes par ce domaine, les endpoints affichés l'utilisent.

## Mettre à jour l'app

Après chaque modification du code :

```powershell
git add .
git commit -m "Description du changement"
git push
```

Render redéploie automatiquement à chaque `git push`.

---

## ⚠️ Limites du plan gratuit Render

| Limite | Conséquence | Solution |
|---|---|---|
| Le service **s'endort après 15 min** sans visite | Le premier envoi après une pause peut prendre jusqu'à ~1 min | Passer le service en **Starter**. En dépannage : un moniteur gratuit (UptimeRobot…) qui appelle `/healthz` toutes les 10 min (reste dans les 750 h gratuites/mois pour un seul service) |
| La base Postgres gratuite **expire après 30 jours** | Les données sont perdues si tu ne passes pas en payant | Passer la base sur une offre payante (instructions ci-dessous) |
| Pas de sauvegarde sur la base gratuite | Risque de perte de données | Base payante |

**Passer en payant.** Dans `render.yaml`, remplace `plan: free` par `plan: starter` pour le service et par `plan: basic-256mb` pour la base. Ensuite `git push` (tu peux aussi changer l'offre dans le tableau de bord Render). Compte environ **15 $/mois** au total, soit deux clients Pro. Vérifie les prix sur https://render.com/pricing.

👉 **Conseil** : passe en payant dès ton premier client payant. Un formulaire de contact qui met une minute à répondre fait fuir les visiteurs.

---

## Autres hébergeurs possibles

Grâce au `Procfile`, CatchForm se déploie aussi tel quel sur **Railway**, **Koyeb** ou **Heroku**. À configurer :
- **Build** : `pip install -r requirements.txt`
- **Démarrage** : `gunicorn wsgi:app --workers 1 --threads 8 --timeout 60`
- **Variables** :
  - `SECRET_KEY` : longue chaîne aléatoire, à générer avec `python -c "import secrets; print(secrets.token_hex(32))"` ;
  - `DATABASE_URL` : URL de ta base Postgres ;
  - `SESSION_COOKIE_SECURE=1`.

---

## ✅ Avant d'accueillir de vrais clients

- [ ] **Mentions légales**, **CGU/CGV** et **politique de confidentialité** (obligatoires en France).
- [ ] **RGPD** : tu stockes les données des visiteurs de tes clients, donc tu es leur **sous-traitant**. Prévois un accord de traitement des données (DPA) dans tes CGU. L'hébergement à Francfort (UE) est un atout.
- [ ] Un **statut** pour facturer (par exemple micro-entreprise).
- [ ] **Stripe** pour encaisser automatiquement (voir la feuille de route du README).
- [ ] Une **base payante** (sauvegardes) et un service qui ne s'endort pas.

---

## 🆘 Dépannage

| Symptôme | Piste |
|---|---|
| Le build échoue | Lis l'onglet **Logs** du service. En cas de souci de version de Python, ajoute la variable `PYTHON_VERSION` avec une version précise (ex. `3.13.5`) |
| « Bad Gateway » / erreur 502 | Regarde les logs : souvent la base n'était pas encore prête. Relance avec **Manual Deploy** → **Deploy latest commit** |
| La première requête est très lente | Normal sur le plan gratuit : le service se réveille |
| Aucun e-mail reçu | Resend → **Logs** : domaine non vérifié ? Pense aussi aux spams |
| « Session expirée » dans le tableau de bord | Recharge la page (le jeton de sécurité est renouvelé) |
