# Service Livraisons

Microservice FastAPI de SenTransport qui gère l'affectation des colis aux livreurs, le suivi du statut des livraisons et leur historique. Il suit le contrat d'API (`docs/contrats-api.md`, section 6).

## Routes

Via la passerelle, le préfixe est `/api/livraisons/` (la passerelle le retire avant d'appeler le service).

| Méthode | Route | Accès | Description |
|---|---|---|---|
| POST | `/` | admin | Affecter un colis à un livreur (201) |
| GET | `/` | connecté | Lister les livraisons (filtres `?livreur_id=` et `?statut=`) |
| GET | `/{id}` | connecté | Détail d'une livraison |
| PATCH | `/{id}/statut` | livreur concerné, admin | Mettre à jour le statut |
| GET | `/{id}/historique` | connecté | Historique des statuts |
| GET | `/health` | public | État du service |

### Exemples

Affecter un colis (jeton admin) :

```json
{ "colis_id": 2, "livreur_id": 2 }
```

Changer le statut (jeton du livreur concerné ou d'un admin) :

```json
{ "statut": "en_transit" }
```

## Statuts

`en_attente` -> `en_transit` -> `livre`, ou `echec`. Les statuts `livre` et `echec` sont finaux : aucune transition n'est possible depuis eux.

## Authentification

Le service vérifie lui-même le jeton JWT (HS256, secret `JWT_SECRET`) envoyé dans `Authorization: Bearer <jeton>`. Il lit `sub` (id de l'utilisateur) et `role` (`client`, `livreur` ou `admin`). Il n'appelle jamais le service Utilisateurs.

## Codes de réponse

| Code | Cas |
|---|---|
| 201 | Affectation créée |
| 400 | Transition de statut interdite |
| 401 | Jeton absent, invalide ou expiré |
| 403 | Droits insuffisants (par exemple un client qui change un statut) |
| 404 | Livraison inexistante, ou colis inexistant à l'affectation |
| 409 | Colis déjà affecté |
| 503 | Service Colis injoignable |

Les erreurs ont le format `{"detail": "message"}`.

## Synchronisation avec le service Colis

Quand le statut d'une livraison change, le service appelle `PATCH {COLIS_URL}/{colis_id}/statut` avec le jeton de l'utilisateur, pour garder les deux statuts identiques. Il lit aussi `GET {COLIS_URL}/{colis_id}` pour vérifier qu'un colis existe avant de l'affecter.

## Choix de conception

- **Ordre des écritures** : le service Colis est mis à jour d'abord, puis la base. Si Colis est injoignable, la réponse est `503` et rien n'est écrit dans la base.
- **Limite connue** : si la base échoue après la mise à jour de Colis, les deux statuts peuvent diverger. Il n'y a pas de transaction répartie entre les deux services.
- **Une livraison par colis** : `colis_id` est unique dans la table `livraisons`.
- **Livreur non vérifié** : le service ne contrôle pas que `livreur_id` est bien un livreur, car il n'écrit pas dans la table `utilisateurs`. La clé étrangère de la base refuse seulement un id inexistant.
- **Historique** : chaque changement de statut ajoute une ligne dans `historique_livraisons`.
- **Accès à la base** : `psycopg2` direct, avec des requêtes paramétrées.

## Variables d'environnement

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL |
| `JWT_SECRET` | Vérification des jetons |
| `COLIS_URL` | Adresse du service Colis (`http://colis:8000`) |

Ces valeurs sont fournies par `docker-compose.yml` et ne doivent jamais être écrites dans le code.

## Tests

Tests unitaires (avec des faux pour la base et le service Colis), à lancer depuis `services/livraisons` :

```powershell
pytest --cov=. --cov-fail-under=60
```

Tests d'intégration (vraie base, vrais services Colis et Utilisateurs), à lancer depuis la racine du projet avec l'application démarrée par `docker compose` :

```powershell
pytest tests/integration -v
```

Ils couvrent le parcours colis -> affectation -> `en_transit` -> `livre` avec synchronisation du colis et historique, le refus d'un client (403), le colis déjà affecté (409), la transition interdite (400) et l'absence de jeton (401). Ils lisent les comptes de démo dans les variables `ADMIN_EMAIL`, `LIVREUR_EMAIL` et `DEMO_PASSWORD` (valeurs par défaut incluses).

## Lancer le service seul avec Docker

```powershell
docker build -t local/livraisons:latest services/livraisons
```

Le service écoute sur le port 8000. `GET /health` renvoie `{"status": "ok", "service": "livraisons"}`.
