# Frontend VAEC (React + TypeScript + Vite)

## Aperçu

Cette interface web fournit une supervision en temps réel du laboratoire d'automobile virtuelle (VAEC) en utilisant le backend FastAPI et le WebSocket.

### Fonctionnalités principales

- **Vue d'ensemble** : État global, vitesse, accélération, distance obstacle, niveau de risque, alertes.
- **Simulation** : Commandes start/stop/pause/resume/reset et configuration des scénarios.
- **Monitoring ECU** : ADAS, VCU, ECU Dashboard — état et dernières activités.
- **Analyseur CAN** : Liste en direct des trames CAN (ID, data, DLC, horodatage).
- **Diagnostics** : Alertes collision, état AEB, erreurs API/WS.
- **Test & Validation** : Liste des scénarios et résultats enregistrés.

### Technologies utilisées

- **React 18** + **TypeScript**
- **Vite** (Build rapide + HMR)
- **Tailwind CSS** + **Framer Motion** (design sombre professionnel)
- **Recharts** (graphiques)
- **socket.io-client** (WebSocket)
- **Lucide React** (icônes)

### Structure des dossiers

```
frontend/
├── src/
│   ├── components/        # UI de base (MetricCard, Sidebar, TopBar, etc.)
│   ├── hooks/             # useWebSocket, useApi
│   ├── pages/             # 6 pages principales
│   ├── services/          # apiService, websocketService
│   ├── types/             # interfaces TypeScript
│   ├── assets/            # logos, images
│   ├── App.tsx           # routage + layout
│   ├── main.tsx          # point d'entrée
│   └── index.css          # styles globals
├── .eslintrc.cjs
├── .gitignore
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

### Installation et démarrage rapide

#### Prérequis
- Node.js >= 20 (14+ fonctionne)
- npm ou pnpm (n'importe lequel)
- Cloner ce dépôt

#### Étapes

1. **Installer le backend** (si non déjà démarré)

```powershell
# Dans le terminal 1 (backend)
cd C:\Projects\Virtual-Automotive-ECU-Lab
$env:PYTHONPATH = "C:\Projects\Virtual-Automotive-ECU-Lab\backend\app"
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

2. **Installer le frontend** (si non déjà installé)

```powershell
# Dans le terminal 2 (frontend)
cd C:\Projects\Virtual-Automotive-ECU-Lab\frontend
npm install
```

3. **Lancer le frontend**

```powershell
npm run dev -- --port 5173
```

4. **Ouvrir** `http://localhost:5173`

### Commandes utiles

| Commande | Action |
|----------|--------|
| `npm run dev` | Lancement en mode développement (HMR) |
| `npm run build` | Build de production (`outDir` → `backend/app/static`) |
| `npm run lint` | Linting TypeScript avec ESLint |
| `npm run preview` | Prévisualisation du build statique |

### Adaptation à la production

- Le répertoire de sortie du build (`dist/`) est configuré pour être copié dans `backend/app/static/` pour la démo.
- Le backend FastAPI peut servir des fichiers statiques depuis `static/` (à vérifier dans `main.py` si nécessaire).
- En production, il faut utiliser un proxy inverse (nginx) pour router `/api/*` vers le backend:8000 et `/static/*` vers le frontend statique.

### Schéma de données des pages (réel, pas de simulation)

Toutes les données proviennent du backend FastAPI et du WebSocket `/api/ws/live`.

#### Vue d'ensemble
- Appelle `/api/status` et `/api/telemetry` toutes les 2s.
- Se connecte à `/api/ws/live` pour la télémétrie instantanée.
- Affiche des cartes de vitesse, accélération, obstacle, état AEB, FCW, risque.

#### Simulation
- Boutons start/stop/pause/resume/reset ↔ appels REST (`/api/simulation/start` etc.)
- Config : `target_speed_kmh`, throttle, obstacle (si l'API accepte les paramètres)

#### Monitoring ECU
- Lit `/api/status` → extrait `vehicle_state` → affiche ADAS, VCU, Dashboard.

#### Analyseur CAN
- `/api/can/frames?limit=100` → affiche tableau trié par horodatage.

#### Diagnostics
- Surveille les erreurs de connexion WebSocket, les alertes collision depuis `/api/telemetry`, le drapeau AEB.

#### Test & Validation
- Lit depuis un endpoint de validation de scénario (ex. `/api/tests/results`) — renvoie seulement ce que le backend fournit.

### Conception d'interface

- **Thème sombre** (palette grise/noir avec accent bleu/vert).
- **Sidebar** : navigation fixe avec icônes.
- **TopBar** : titre de la page, indicateur de connexion WebSocket, date/heure.
- **Métriques** : cartes avec valeurs, unités, état (neutre/warning/error/success).
- **Tableaux** : trames CAN avec pagination, tri.
- **Graphiques** : Recharts pour la vitesse vs temps, accélération, distance obstacle.
- **Responsive** : s'adapte aux mobiles.

### Bonnes pratiques de sécurité

- **CORS** : Le backend FastAPI inclut `allow_origins=["*"]` (à restreindre en production).
- **Proxy Vite** : Toutes les requêtes `/api` vont vers `http://localhost:8000`.
- **WebSocket** : `socket.io-client` avec base URL vide → reçoit le chemin relatif `/api/ws/live`.
- **Sanitisation des erreurs** : Affichage des messages d'erreur, pas de stack trace exposés.

### Problèmes connus / à résoudre

1. **Appel npm bloqué** : L'environnement restreint bloque temporaireement certaines commandes shell. Solutions proposées :
   - Utiliser `npm run` de manière non interactive.
   - Supprimer le cache (`npm cache clean --force`).
   - Utiliser `--legacy-peer-deps` si les problèmes de peer dependency persistent.

2. **Types TypeScript** : Les types pour les données backend peuvent être ajoutés plus tard.

3. **Tests frontend** : Non implémentés ; une future itération ajoutera Vitest + React Testing Library.

### Licence

Propriétaire du laboratoire VAEC.