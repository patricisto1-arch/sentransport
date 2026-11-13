# Tester toute l'application SenTransport en local

Ce guide est pour la branche de test `test/integration-equipe`. Elle réunit `develop`, le `init.sql` aligné sur le contrat (Ryghen) et le service Livraisons avec ses tests d'intégration (Boveldy). **Ne pas ouvrir de Pull Request depuis cette branche vers `develop`** : elle sert uniquement à tester.

## Pourquoi il faut construire les images

Le `docker-compose.yml` n'a pas de section `build` : il télécharge des images `${REGISTRY}/<service>:${TAG}` publiées par la CI. En local, ces images n'existent pas, donc on les construit nous-mêmes avec le nom `local/<service>:latest`.

## Prérequis

- Docker Desktop installé et **lancé** (attendre « Engine running »).
- Le port **80** libre sur ton PC (fermer un éventuel serveur web ou autre Nginx).
- Git.

## Étapes (PowerShell, depuis la racine du projet)

**1. Récupérer la branche de test**

```powershell
git fetch --all
git checkout test/integration-equipe
```

Si tu as des modifications en cours sur ta branche, commite-les ou mets-les de côté avant (`git stash`).

**2. Créer le fichier `.env`** à la racine (il est ignoré par Git : ne jamais le commiter, ce sont des valeurs de test) :

```powershell
@"
REGISTRY=local
TAG=latest
POSTGRES_PASSWORD=test_local_pwd_123
JWT_SECRET=secret-de-test-local-au-moins-32-caracteres-123456
"@ | Set-Content -Path .env -Encoding ascii
```

**3. Construire les 4 images** (la première fois, compter plusieurs minutes par image à cause des téléchargements) :

```powershell
docker build -t local/colis:latest services/colis
docker build -t local/utilisateurs:latest services/utilisateurs
docker build -t local/livraisons:latest services/livraisons
docker build -t local/frontend:latest frontend
```

**4. Lancer l'application** (le terminal reste occupé, c'est normal) :

```powershell
docker compose up
```

Attendre que les logs se calment. On doit voir la base exécuter `init.sql`, puis `GET /health ... 200 OK` pour les trois services.

**5. Ouvrir** `http://localhost` dans le navigateur.

## Comptes de démo

| Rôle | E-mail | Mot de passe |
|---|---|---|
| Administrateur | `admin.demo@sentransport.sn` | `Demo1234!` |
| Livreur | `livreur.demo@sentransport.sn` | `Demo1234!` |
| Client | `client.demo@sentransport.sn` | `Demo1234!` |

Un nouveau compte créé avec l'inscription est toujours un **client**. Un jeton est valable 1 heure : se reconnecter ensuite.

## Lancer les tests d'intégration (optionnel)

Application démarrée, dans un **second terminal**, depuis la racine :

```powershell
pip install pytest httpx
pytest tests/integration -v
```

Résultat attendu : 5 tests qui passent.

## Arrêter et repartir de zéro

- Arrêter : `Ctrl+C` dans le terminal de `docker compose up`, puis `docker compose down`.
- Repartir d'une base vide (la base garde ses données entre deux lancements) : `docker compose down -v`, puis `docker compose up`.

## Problèmes fréquents

| Symptôme | Cause probable | Solution |
|---|---|---|
| `failed to connect to the docker API` | Docker Desktop n'est pas lancé | Le lancer et attendre qu'il soit prêt |
| `invalid reference format` ou variable `REGISTRY` non définie | Le `.env` manque ou est mal placé | Le recréer à la racine du projet (étape 2) |
| `No such image: local/...` ou `pull access denied` | Les images n'ont pas été construites | Refaire l'étape 3 |
| `port is already allocated` (port 80) | Un autre programme utilise le port 80 | Le fermer, puis relancer |
| Connexion refusée (« Données invalides ») avec un compte de démo | Base créée avec un ancien `init.sql` | `docker compose down -v`, puis `docker compose up` |
| Après un `git pull`, le code semble ancien | Les images n'ont pas été reconstruites | Refaire l'étape 3 pour les services modifiés |

## Ce qu'il faut tester et signaler

Connexion avec chaque rôle, création d'un colis, affectation à un livreur (admin), changement de statut (livreur), historique d'une livraison, droits refusés (par exemple un client qui change un statut). Pour signaler un bug : service concerné, ce qui a été fait, message d'erreur, et les logs du terminal de `docker compose up`.
