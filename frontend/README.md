# AlienShot Console (frontend)

Interface Vue 3 servant la console admin sécurisée et les pages de partage public. Les appels API pointent vers le backend Flask défini dans `../backend`.

## Variables d'environnement

Copiez `.env.example` puis ajustez :

```
VITE_API_BASE_URL=http://localhost:5000
```

## Scripts utiles

```bash
npm install
npm run dev
npm run build
npm run preview
```

`npm run dev` démarre Vite (port 5173) et consomme l'API indiquée par `VITE_API_BASE_URL`.
