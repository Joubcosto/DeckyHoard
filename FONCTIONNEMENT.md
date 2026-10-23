# Fonctionnement du projet `DeckyHoard` (Hoard Sync)

`DeckyHoard` est un plugin **Decky Loader** minimaliste pour SteamOS et Bazzite (Game Mode). Son rôle est de servir d'interface graphique légère au-dessus de la CLI officielle **[Hoard](https://github.com/rleeon/hoard)** (`hoard` et son démon de synchronisation `hoardd`), sans réinventer la logique métier déjà présente dans le binaire Rust de Hoard.

---

## 1. Architecture Générale

Le projet est divisé en deux parties qui communiquent de manière asynchrone via le pont RPC de Decky Loader (`@decky/api`) :

```
┌──────────────────────────────────────────────────────────────┐
│                  Frontend (Game Mode UI)                     │
│  src/index.tsx  ──(compilé par Rollup)──►  dist/index.js     │
│  Composants @decky/ui + appels RPC via call("method_name")   │
└──────────────────────────────┬───────────────────────────────┘
                               │ Pont RPC Decky Loader
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Backend Python (main.py)                  │
│  Classe `Plugin` ──► Singleton `HoardBackend`                │
│  Exécute les commandes `hoard` en tant qu'utilisateur local  │
└──────────────────────────────┬───────────────────────────────┘
                               │ Sous-processus isolés
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                 CLI & Démon Hoard (Rust)                     │
│  ~/.local/bin/hoard   (commandes --json)                     │
│  ~/.local/bin/hoardd  (service systemd hoard-sync.service)   │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Backend Python (`main.py`)

### A. Isolation de l'utilisateur et de l'environnement
Decky Loader exécute les backends de plugins en tant que `root` à l'intérieur d'un environnement PyInstaller. Cela pose deux problèmes classiques sur SteamOS/Bazzite que `main.py` résout :

1. **Exécution non-root (`_get_decky_user_info`)** :
   - Le plugin détecte automatiquement l'utilisateur réel de la session Steam (`deck` sur SteamOS, ou l'utilisateur principal sur Bazzite via `decky.DECKY_USER` et le chemin `/home/<user>` ou `/var/home/<user>`).
   - Chaque sous-processus est lancé avec les droits de cet utilisateur (`user=uid`, `group=gid`) et dans son répertoire personnel (`HOME`).
2. **Nettoyage de `LD_LIBRARY_PATH` (`_get_user_env`)** :
   - Decky Loader injecte ses propres bibliothèques (`LD_LIBRARY_PATH` / `LD_PRELOAD`) qui entrent en conflit avec les binaires système (`systemctl`, `curl`, `hoard`).
   - `_get_user_env` supprime `LD_LIBRARY_PATH` et `LD_PRELOAD`, configure les variables `XDG_*` ainsi que le bus DBus utilisateur (`DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/<uid>/bus`) pour permettre à `systemctl --user` et à `hoard` de communiquer avec le démon `hoardd`.

### B. Le contrat `--json` de Hoard (`_run_hoard`)
La CLI `hoard` fournit un contrat JSON strict pour les outils et scripts :
- En cas de succès (code de retour `0`) :
  ```json
  { "ok": true, "data": { ... } }
  ```
- En cas d'erreur (code de retour `!= 0`) :
  ```json
  { "ok": false, "error": { "code": "...", "message": "..." } }
  ```

La méthode `_run_hoard` exécute directement `~/.local/bin/hoard` (sans passer par un shell intermédiaire) et parse automatiquement cette enveloppe JSON.

### C. Les méthodes exposées au Frontend

| Méthode Python | Commandes exécutées | Rôle |
| :--- | :--- | :--- |
| `get_status()` | `hoard --version`<br>`systemctl --user is-active hoard-sync.service`<br>`hoard whoami --json` | Vérifie en parallèle si Hoard est installé, si le service de synchro tourne en tâche de fond, et si l'utilisateur est connecté (gère aussi le mode hors-ligne via le code `network` / exit `6`). |
| `install_hoard()` | `curl -fsSL .../install.sh \| HOARD_HEADLESS=1 HOARD_NONINTERACTIVE=1 sh` | Télécharge et installe `hoard` et `hoardd` dans `~/.local/bin` via le script officiel en mode sans interface graphique (`--headless`). |
| `get_games(force_refresh)` | `hoard saves --json`<br>`hoard scan --json` | Croise les sauvegardes déjà suivies localement (`hoard saves --json`, instantané et hors-ligne) avec la détection automatique des jeux installés (`hoard scan --json`, qui scanne Steam, Proton et Ludusavi). |
| `track_game(name, slug)` | `hoard track --slug <slug>`<br>`hoard backup <save_id>` | Ajoute un jeu au suivi automatique (ce qui notifie immédiatement le démon `hoardd` par IPC) puis envoie immédiatement la première sauvegarde sur le serveur/cloud. |
| `untrack_game(save_id)` | `hoard save untrack <save_id> --json` | Arrête de surveiller le dossier de sauvegarde sur la machine locale tout en conservant l'historique des sauvegardes dans le cloud. |
| `force_sync()` | `hoard sync start` *(si arrêté)*<br>`hoard saves --json`<br>`hoard backup <save_id>` | Démarre le démon s'il est inactif et force l'envoi d'un snapshot pour chaque sauvegarde suivie non mise en pause. |

---

## 3. Catégorisation des jeux (`get_games`)

Plutôt que de parser manuellement les fichiers Steam (`.vdf` / `.acf`), le plugin utilise directement la sortie de `hoard scan --json` et `hoard saves --json` pour classer les jeux en **3 sections** :

1. **Jeux suivis (`tracked`)** :
   - Jeux présents dans `hoard saves --json` ou marqués `tracked: true` par `hoard scan --json`.
   - Contient le `save_id` (UUID), l'état `paused`, et le numéro de la dernière version sauvegardée (`last_version_num`).
2. **Prêts à être suivis (`ready_to_track`)** :
   - Jeux détectés par `hoard scan --json` avec `tracked: false` et `needs_folder: false` (Hoard a trouvé leur dossier de sauvegarde sur le disque).
   - Un clic suffit pour les suivre via `hoard track --slug <slug>`.
3. **Dossier de sauvegarde introuvable (`missing_folder`)** :
   - Jeux installés détectés par `hoard scan --json` avec `needs_folder: true` (`paths` est vide, par exemple parce que le jeu n'a encore jamais été lancé pour créer son préfixe Proton ou son dossier de sauvegarde).

---

## 4. Frontend React (`src/index.tsx`)

Le fichier `src/index.tsx` utilise `@decky/api` et `@decky/ui` :
- **Localisation automatique (`FR` / `EN`)** : Détecte la langue du client Steam (`SteamClient.Settings.GetCurrentLanguage()`) ou du navigateur.
- **Écran d'installation** : Si `status.installed` est `false`, affiche uniquement un bouton permettant d'installer la CLI en un clic.
- **Section Service & Synchronisation** :
  - Affiche un avertissement si `status.logged_in` est `false` (invite à lancer `hoard login` une fois en Mode Bureau).
  - Affiche l'état du démon (`ONLINE` / `OFFLINE`) ainsi que le compte actif (`email` ou `username`).
  - Permet de lancer une synchronisation manuelle (**Synchroniser maintenant**) ou de relancer la détection (**Rafraîchir la bibliothèque**).
- **Listes de jeux interactives** :
  - Cliquer sur un jeu dans **Prêts à être suivis** lance `track_game`.
  - Cliquer sur un jeu dans **Jeux suivis** lance `untrack_game` (arrêt du suivi local).

---

## 5. Scripts de Build et Déploiement

- **`pnpm run build`** : Compile `src/index.tsx` vers `dist/index.js` via Rollup (`rollup.config.js`).
- **`./package.sh`** : Compile le frontend et génère une archive `decky-hoard.zip` prête à être installée dans Decky Loader.
- **`./deploy.sh [user@ip]`** : Compile le plugin et le déploie directement dans `~/homebrew/plugins/decky-hoard` (en local sur SteamOS/Bazzite ou à distance via SSH) puis redémarre `plugin_loader.service`.
