# SenTransport : contrats d'API et schéma de données

Ce document est la référence commune de l'équipe. **Toute modification passe par le chef de projet** et par une Pull Request, pour que les services et le frontend restent compatibles.

## 1. Règles générales

- Tous les services écoutent sur le port **8000** dans leur conteneur.
- Le frontend appelle **uniquement la passerelle Nginx** (port 80), qui retire le préfixe `/api/<service>` avant de transmettre la requête.
- Format des échanges : **JSON**, encodage UTF-8, noms de champs en `snake_case`, dates au format ISO 8601 (`2026-11-12T14:30:00Z`).
- Chaque service expose `GET /health` qui renvoie `{"status": "ok", "service": "<nom>"}`.
- Les erreurs suivent le format FastAPI : `{"detail": "message d'erreur"}`.
- Codes HTTP : `200` succès, `201` création, `204` suppression, `400` données invalides, `401` non authentifié, `403` droits insuffisants, `404` introuvable, `409` conflit (ex. e-mail déjà utilisé).

| Service | Préfixe via la passerelle | Chemin interne |
|---|---|---|
| Utilisateurs | `/api/utilisateurs/` | `/` |
| Colis | `/api/colis/` | `/` |
| Livraisons | `/api/livraisons/` | `/` |

Exemple : `GET /api/colis/12` arrive au service Colis sur `GET /12`.
**Attention** : la collection se termine par un `/` côté passerelle (`/api/colis/`).

## 2. Authentification (JWT)

- Le service **Utilisateurs** délivre le jeton à la connexion.
- Algorithme **HS256**, secret partagé dans la variable d'environnement `JWT_SECRET`.
- Contenu du jeton : `sub` (id de l'utilisateur, en texte), `role` (`client`, `livreur` ou `admin`), `exp` (expiration, 1 heure).
- Les autres services **vérifient eux-mêmes** le jeton avec `JWT_SECRET` : ils n'appellent pas le service Utilisateurs.
- Le frontend envoie `Authorization: Bearer <jeton>` sur toutes les routes protégées.

## 3. Statuts

**Statuts d'un colis et d'une livraison** (mêmes valeurs) :
`en_attente` → `en_transit` → `livre`, ou `echec`.

**Rôles** : `client`, `livreur`, `admin`.

## 4. Service Utilisateurs

| Méthode | Route (via la passerelle) | Accès | Description |
|---|---|---|---|
| POST | `/api/utilisateurs/auth/register` | public | Créer un compte |
| POST | `/api/utilisateurs/auth/login` | public | Se connecter, reçoit un jeton |
| GET | `/api/utilisateurs/me` | connecté | Profil de l'utilisateur connecté |
| GET | `/api/utilisateurs/livreurs` | admin | Liste des livreurs |

**POST /auth/register**

```json
{ "nom": "Awa Diop", "email": "awa@exemple.sn", "mot_de_passe": "motdepasse123", "role": "client" }
```

Réponse `201` :

```json
{ "id": 1, "nom": "Awa Diop", "email": "awa@exemple.sn", "role": "client" }
```

**POST /auth/login**

```json
{ "email": "awa@exemple.sn", "mot_de_passe": "motdepasse123" }
```

Réponse `200` :

```json
{ "access_token": "<jeton>", "token_type": "bearer" }
```

## 5. Service Colis

| Méthode | Route (via la passerelle) | Accès | Description |
|---|---|---|---|
| POST | `/api/colis/` | client, admin | Créer un colis |
| GET | `/api/colis/` | connecté | Lister les colis (un client ne voit que les siens) |
| GET | `/api/colis/{id}` | connecté | Détail d'un colis |
| PUT | `/api/colis/{id}` | client (propriétaire), admin | Modifier un colis encore `en_attente` |
| DELETE | `/api/colis/{id}` | admin | Supprimer un colis |
| PATCH | `/api/colis/{id}/statut` | livreur, admin | Changer le statut |

**POST /** :

```json
{
  "destinataire_nom": "Moussa Ndiaye",
  "destinataire_adresse": "Rue 10, Pikine",
  "description": "Carton de livres",
  "poids_kg": 2.5
}
```

L'expéditeur est l'utilisateur du jeton. Réponse `201` :

```json
{
  "id": 12,
  "expediteur_id": 1,
  "destinataire_nom": "Moussa Ndiaye",
  "destinataire_adresse": "Rue 10, Pikine",
  "description": "Carton de livres",
  "poids_kg": 2.5,
  "statut": "en_attente",
  "created_at": "2026-11-12T14:30:00Z"
}
```

**PATCH /{id}/statut** :

```json
{ "statut": "en_transit" }
```

## 6. Service Livraisons

| Méthode | Route (via la passerelle) | Accès | Description |
|---|---|---|---|
| POST | `/api/livraisons/` | admin | Affecter un colis à un livreur |
| GET | `/api/livraisons/` | connecté | Lister (filtres `?livreur_id=` et `?statut=`) |
| GET | `/api/livraisons/{id}` | connecté | Détail d'une livraison |
| PATCH | `/api/livraisons/{id}/statut` | livreur concerné, admin | Mettre à jour le statut |
| GET | `/api/livraisons/{id}/historique` | connecté | Historique des statuts |

**POST /** :

```json
{ "colis_id": 12, "livreur_id": 4 }
```

Réponse `201` :

```json
{
  "id": 7,
  "colis_id": 12,
  "livreur_id": 4,
  "statut": "en_attente",
  "created_at": "2026-11-12T15:00:00Z",
  "updated_at": "2026-11-12T15:00:00Z"
}
```

**PATCH /{id}/statut** :

```json
{ "statut": "livre" }
```

Quand le statut d'une livraison change, le service Livraisons appelle `PATCH {COLIS_URL}/{colis_id}/statut` du service Colis pour garder les deux synchronisés. `COLIS_URL` vaut `http://colis:8000` (variable déjà définie dans `docker-compose.yml`). Le jeton de l'utilisateur est transmis dans l'en-tête `Authorization`.

## 7. Schéma de la base PostgreSQL

Base `sentransport`, **partagée** par les trois services, créée par `database/init.sql` (Membre 3). Chaque service n'écrit que dans ses propres tables.

**utilisateurs** (service Utilisateurs)

| Colonne | Type | Contraintes |
|---|---|---|
| id | SERIAL | clé primaire |
| nom | VARCHAR(100) | obligatoire |
| email | VARCHAR(150) | unique, obligatoire |
| mot_de_passe_hash | VARCHAR(255) | obligatoire (jamais de mot de passe en clair) |
| role | VARCHAR(20) | `client`, `livreur` ou `admin` |
| created_at | TIMESTAMP | défaut maintenant |

**colis** (service Colis)

| Colonne | Type | Contraintes |
|---|---|---|
| id | SERIAL | clé primaire |
| expediteur_id | INTEGER | référence `utilisateurs(id)` |
| destinataire_nom | VARCHAR(100) | obligatoire |
| destinataire_adresse | VARCHAR(255) | obligatoire |
| description | TEXT | facultatif |
| poids_kg | NUMERIC(6,2) | supérieur à 0 |
| statut | VARCHAR(20) | `en_attente`, `en_transit`, `livre`, `echec`, défaut `en_attente` |
| created_at | TIMESTAMP | défaut maintenant |

**livraisons** (service Livraisons)

| Colonne | Type | Contraintes |
|---|---|---|
| id | SERIAL | clé primaire |
| colis_id | INTEGER | référence `colis(id)`, unique |
| livreur_id | INTEGER | référence `utilisateurs(id)` |
| statut | VARCHAR(20) | mêmes valeurs que `colis.statut` |
| created_at | TIMESTAMP | défaut maintenant |
| updated_at | TIMESTAMP | défaut maintenant |

**historique_livraisons** (service Livraisons)

| Colonne | Type | Contraintes |
|---|---|---|
| id | SERIAL | clé primaire |
| livraison_id | INTEGER | référence `livraisons(id)` |
| statut | VARCHAR(20) | statut enregistré |
| date_changement | TIMESTAMP | défaut maintenant |

## 8. Variables d'environnement (déjà fournies par `docker-compose.yml`)

| Variable | Utilisée par | Rôle |
|---|---|---|
| `DATABASE_URL` | les 3 services | Connexion PostgreSQL |
| `JWT_SECRET` | les 3 services | Signature et vérification des jetons |
| `COLIS_URL` | Livraisons | Adresse interne du service Colis |

Ne jamais écrire ces valeurs dans le code : lire `os.getenv(...)`.

## 9. Rappel du workflow Git

1. Prendre une issue, créer la branche `feature/<nom-de-la-tache>` à partir de `develop`.
2. Commits courts et clairs, par exemple `feat: création d'un colis`.
3. Ouvrir une Pull Request vers `develop`, attendre le workflow vert et une relecture.
4. Ne jamais pousser directement sur `main` ni `develop`.
