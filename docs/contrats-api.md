# SenTransport : contrats d'API et schéma de données

Ce document décrit l'API **telle qu'elle est implémentée** (routes relevées sur les services en fonctionnement). Il remplace la première version du contrat : les identifiants sont des **entiers**, le rôle administrateur s'appelle **`admin`**, et l'inscription ne crée que des clients.

Toute modification d'une route ou d'un format passe par le chef de projet et par une Pull Request, pour que les services et le frontend restent compatibles.

## 1. Règles générales

- Le navigateur n'appelle que la **passerelle Nginx** (port 80), qui retire le préfixe `/api/<service>` avant de transmettre la requête au service.
- Chaque service écoute sur le port **8000** dans son conteneur.
- Format des échanges : **JSON**, UTF-8, champs en `snake_case`, dates en ISO 8601 (`2026-11-12T14:30:00`).
- Chaque service expose `GET /health`, qui renvoie `{"status": "ok", ...}`.
- Les identifiants (`id`, `colis_id`, `livreur_id`, `expediteur_id`) sont des **entiers**.

| Service | Préfixe via la passerelle | Chemin interne |
|---|---|---|
| Utilisateurs | `/api/utilisateurs/` | `/` |
| Colis | `/api/colis/` | `/` |
| Livraisons | `/api/livraisons/` | `/` |

Exemple : `GET /api/colis/12` arrive au service Colis sur `GET /12`. **Les collections se terminent par un `/`** côté passerelle (`/api/colis/`), sinon la requête est traitée comme celle du frontend.

### Codes de réponse

| Code | Signification |
|---|---|
| 200 | Succès |
| 201 | Création |
| 204 | Suppression, sans contenu |
| 400 | Données invalides (service Utilisateurs) ou transition de statut impossible (service Livraisons) |
| 401 | Jeton absent, invalide ou expiré |
| 403 | Droits insuffisants |
| 404 | Ressource introuvable |
| 409 | Conflit (e-mail déjà utilisé, colis déjà affecté, transition impossible côté Colis) |
| 422 | Données invalides (services Colis et Livraisons) |
| 503 | Service Colis indisponible (vu depuis le service Livraisons) |

Les erreurs ont la forme `{"detail": "message"}`. Pour un `422`, `detail` est une liste décrivant chaque champ invalide.

## 2. Authentification (JWT)

- Le service **Utilisateurs** délivre le jeton à la connexion.
- Algorithme **HS256**, signé avec le secret partagé `JWT_SECRET` (au moins 32 caractères).
- Contenu du jeton : `sub` (identifiant de l'utilisateur, en texte, par exemple `"3"`), `role` (`client`, `livreur` ou `admin`) et `exp` (expiration, **1 heure** après la connexion).
- Les services **Colis** et **Livraisons** vérifient eux-mêmes le jeton avec `JWT_SECRET` ; ils n'appellent pas le service Utilisateurs.
- Le client envoie `Authorization: Bearer <jeton>` sur toutes les routes protégées.
- Les mots de passe sont stockés sous forme de hash **Argon2id**.

## 3. Statuts

Statuts d'un colis **et** d'une livraison : `en_attente`, `en_transit`, `livre`, `echec`.

| Statut actuel | Statuts autorisés ensuite |
|---|---|
| `en_attente` | `en_transit`, `echec` |
| `en_transit` | `livre`, `echec` |
| `livre` | aucun |
| `echec` | aucun |

Toute autre transition est refusée (`409` côté Colis, `400` côté Livraisons).

## 4. Service Utilisateurs

| Méthode | Route (via la passerelle) | Accès | Description |
|---|---|---|---|
| POST | `/api/utilisateurs/auth/register` | public | Créer un compte |
| POST | `/api/utilisateurs/auth/login` | public | Se connecter, reçoit un jeton |
| GET | `/api/utilisateurs/me` | connecté | Profil de l'utilisateur connecté |
| GET | `/api/utilisateurs/livreurs` | `admin` | Liste des livreurs, triés par nom |
| GET | `/api/utilisateurs/health` | public | État du service |

**POST /auth/register**

| Champ | Type | Règle |
|---|---|---|
| `nom` | texte | obligatoire, 2 à 100 caractères |
| `email` | texte | obligatoire, adresse e-mail valide |
| `mot_de_passe` | texte | obligatoire, 8 à 128 caractères |
| `role` | texte | facultatif ; seule la valeur `client` est acceptée |

```json
{ "nom": "Awa Diop", "email": "awa@exemple.sn", "mot_de_passe": "motdepasse123" }
```

Réponse `201` :

```json
{ "id": 4, "nom": "Awa Diop", "email": "awa@exemple.sn", "role": "client" }
```

Erreurs : `403` si le rôle demandé n'est pas `client` (les comptes livreur et administrateur ne se créent pas par l'inscription ; ceux de la démonstration viennent de `database/init.sql`), `409` si l'e-mail est déjà utilisé, `400` si les données sont invalides.

**POST /auth/login**

```json
{ "email": "awa@exemple.sn", "mot_de_passe": "motdepasse123" }
```

Réponse `200` :

```json
{ "access_token": "<jeton>", "token_type": "bearer" }
```

Erreur : `401` « Identifiants incorrects ».

## 5. Service Colis

| Méthode | Route (via la passerelle) | Accès | Description |
|---|---|---|---|
| POST | `/api/colis/` | `client`, `admin` | Créer un colis |
| GET | `/api/colis/` | `client`, `livreur`, `admin` | Lister les colis (un client ne voit que les siens) |
| GET | `/api/colis/{id}` | `client`, `livreur`, `admin` | Détail d'un colis (`404` si le colis appartient à un autre client) |
| PUT | `/api/colis/{id}` | `client` (propriétaire), `admin` | Modifier un colis, seulement s'il est `en_attente` (sinon `409`) |
| DELETE | `/api/colis/{id}` | `admin` | Supprimer un colis (`409` s'il est lié à une livraison) |
| PATCH | `/api/colis/{id}/statut` | `livreur`, `admin` | Changer le statut, selon les transitions de la section 3 |

**POST /** (l'expéditeur est l'utilisateur du jeton) :

| Champ | Type | Règle |
|---|---|---|
| `destinataire_nom` | texte | obligatoire, 1 à 100 caractères |
| `destinataire_adresse` | texte | obligatoire, 1 à 255 caractères |
| `description` | texte | facultatif |
| `poids_kg` | nombre | obligatoire, strictement supérieur à 0 |

```json
{
  "destinataire_nom": "Moussa Ndiaye",
  "destinataire_adresse": "Rue 10, Pikine",
  "description": "Carton de livres",
  "poids_kg": 2.5
}
```

Réponse `201` (le poids est renvoyé en **texte**) :

```json
{
  "id": 12,
  "expediteur_id": 4,
  "destinataire_nom": "Moussa Ndiaye",
  "destinataire_adresse": "Rue 10, Pikine",
  "description": "Carton de livres",
  "poids_kg": "2.50",
  "statut": "en_attente",
  "created_at": "2026-11-12T14:30:00"
}
```

**PUT /{id}** accepte les mêmes champs que la création, tous facultatifs. **PATCH /{id}/statut** reçoit `{ "statut": "en_transit" }`.

## 6. Service Livraisons

| Méthode | Route (via la passerelle) | Accès | Description |
|---|---|---|---|
| POST | `/api/livraisons/` | `admin` | Affecter un colis à un livreur |
| GET | `/api/livraisons/` | connecté | Lister, avec les filtres `?livreur_id=` et `?statut=` |
| GET | `/api/livraisons/{id}` | connecté | Détail d'une livraison |
| GET | `/api/livraisons/{id}/historique` | connecté | Historique des statuts |
| PATCH | `/api/livraisons/{id}/statut` | `livreur` (le sien), `admin` | Changer le statut |

**POST /** :

```json
{ "colis_id": 12, "livreur_id": 2 }
```

Réponse `201` :

```json
{
  "id": 7,
  "colis_id": 12,
  "livreur_id": 2,
  "statut": "en_attente",
  "created_at": "2026-11-12T15:00:00",
  "updated_at": "2026-11-12T15:00:00"
}
```

Erreurs : `404` si le colis n'existe pas, `409` s'il est déjà affecté (une seule livraison par colis), `503` si le service Colis est indisponible.

**PATCH /{id}/statut** reçoit `{ "statut": "livre" }`. Un livreur ne peut modifier que ses propres livraisons (`403` sinon). Le service Livraisons met d'abord à jour le statut du colis auprès du service Colis, en transmettant le jeton de l'utilisateur, puis enregistre le sien : si le service Colis refuse, rien n'est modifié.

**GET /{id}/historique** renvoie la liste des changements :

```json
[ { "id": 1, "livraison_id": 7, "statut": "en_attente", "date_changement": "2026-11-12T15:00:00" } ]
```

## 7. Schéma de la base PostgreSQL

Base `sentransport`, **partagée** par les trois services, créée par `database/init.sql` au premier démarrage du conteneur. Chaque service n'écrit que dans ses propres tables.

**utilisateurs** (service Utilisateurs)

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | clé primaire |
| `nom` | VARCHAR(100) | obligatoire |
| `email` | VARCHAR(150) | unique, obligatoire |
| `mot_de_passe_hash` | VARCHAR(255) | obligatoire (hash Argon2id, jamais de mot de passe en clair) |
| `role` | VARCHAR(20) | `client`, `livreur` ou `admin` |
| `created_at` | TIMESTAMP | défaut maintenant |

**colis** (service Colis)

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | clé primaire |
| `expediteur_id` | INTEGER | référence `utilisateurs(id)` |
| `destinataire_nom` | VARCHAR(100) | obligatoire |
| `destinataire_adresse` | VARCHAR(255) | obligatoire |
| `description` | TEXT | facultatif |
| `poids_kg` | NUMERIC(6,2) | supérieur à 0 |
| `statut` | VARCHAR(20) | `en_attente`, `en_transit`, `livre` ou `echec`, défaut `en_attente` |
| `created_at` | TIMESTAMP | défaut maintenant |

**livraisons** (service Livraisons)

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | clé primaire |
| `colis_id` | INTEGER | référence `colis(id)`, **unique** (une livraison par colis) |
| `livreur_id` | INTEGER | référence `utilisateurs(id)` |
| `statut` | VARCHAR(20) | mêmes valeurs que `colis.statut` |
| `created_at` | TIMESTAMP | défaut maintenant |
| `updated_at` | TIMESTAMP | défaut maintenant |

**historique_livraisons** (service Livraisons)

| Colonne | Type | Contraintes |
|---|---|---|
| `id` | SERIAL | clé primaire |
| `livraison_id` | INTEGER | référence `livraisons(id)`, supprimée avec la livraison |
| `statut` | VARCHAR(20) | statut enregistré |
| `date_changement` | TIMESTAMP | défaut maintenant |

Le script charge aussi trois comptes de démonstration (client, livreur, administrateur), un colis et sa livraison.

## 8. Variables d'environnement

Elles sont fournies par `docker-compose.yml` à partir du fichier `.env` (en local) ou du workflow (en déploiement).

| Variable | Utilisée par | Rôle |
|---|---|---|
| `DATABASE_URL` | les trois services | Connexion PostgreSQL |
| `JWT_SECRET` | les trois services | Signature et vérification des jetons |
| `COLIS_URL` | Livraisons | Adresse interne du service Colis (`http://colis:8000`) |
| `POSTGRES_PASSWORD` | base de données | Mot de passe de l'utilisateur `sentransport` |
| `REGISTRY` et `TAG` | `docker-compose.yml` | Préfixe et étiquette des images à lancer |

Aucune valeur sensible ne doit être écrite dans le code : les services la lisent avec `os.getenv(...)`.

## 9. Points à connaître

- **Accès aux livraisons** : les routes `GET` du service Livraisons ne filtrent pas selon le rôle (un client connecté peut lister toutes les livraisons). À corriger si l'application sort du cadre de la démonstration.
- **Motif d'échec** : l'API ne stocke pas de motif quand une livraison échoue.
- **Formats d'erreur** : Utilisateurs répond `400` aux données invalides, Colis et Livraisons répondent `422`.
- **Traitement des transitions** : une transition impossible donne `409` côté Colis et `400` côté Livraisons.
