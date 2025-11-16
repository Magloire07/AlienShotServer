# AlienShotServer

Plateforme complète permettant de réceptionner des photos envoyées depuis l'application Kotlin, de les stocker dans SQLite et de les mettre à disposition via une console admin (protégée par mot de passe) et des liens publics générés sous forme de QR codes.

## Architecture

- **backend/** – API Flask + SQLite + stockage disque (`instance/uploads`). Expose l'ingestion (`POST /images/add`), la console sécurisée (`GET/DELETE /photos`) et les partages tokens (`/shares`).
- **frontend/** – SPA Vue 3 (Vite) avec deux vues : console admin et galerie partagée. Génère le QR localement grâce à `qrcode.vue`.
- **.github/workflows/** – pipeline GitHub Actions pour builder et pousser les images Docker du front et du back vers GHCR.
- **Dockerfiles** – un Dockerfile par service pour produire des images prêtes à déployer.

## Prérequis

- Python 3.11+
- Node.js 20+
- SQLite (embarqué)

## Backend (Flask)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # ajustez les valeurs si besoin
flask --app app run --debug
```

- `ADMIN_PASSWORD` change le mot de passe de la console (défaut `admin`).
- `SHARE_BASE_URL` doit pointer vers l'hôte front (ex. `https://monfront/share`).
- Les fichiers uploadés sont stockés dans `instance/uploads` (ignoré par git).

### Tests

```bash
cd backend
pytest
```

## Frontend (Vue 3)

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

La variable `VITE_API_BASE_URL` doit cibler l'URL publique de l'API Flask.

## Flux fonctionnels

1. L'appareil Kotlin POSTe des images sur `/images/add` (multipart). Les fichiers sont horodatés et enregistrés sur disque + SQLite.
2. La console admin (`/admin`) affiche la galerie (ordre anti-chronologique) après saisie du mot de passe.
3. L'administrateur peut sélectionner plusieurs photos, générer un lien de partage (QR) ou supprimer les éléments.
4. Le lien public (`/share/<token>`) liste uniquement les photos choisies. Les utilisateurs peuvent sélectionner un sous-ensemble pour télécharger un zip ou tout récupérer.

## Docker

Deux Dockerfiles (front/back) sont fournis. Exemple de build local :

```bash
docker build -t alienshot-backend ./backend
docker build -t alienshot-frontend ./frontend
```

## CI/CD

`.github/workflows/docker-images.yml` construit et pousse automatiquement les deux images Docker vers GHCR (`ghcr.io/<owner>/alienshot-frontend` et `...-backend`). Définissez les secrets `CR_PAT` (PAT GitHub) et `REGISTRY_USER` si nécessaire.