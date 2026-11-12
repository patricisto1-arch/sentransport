# Service Utilisateurs et modèle de données — SenTransport

Le service FastAPI est implémenté dans `services/utilisateurs/main.py`. PostgreSQL est la base partagée; `database/init.sql` crée les tables et les comptes de démonstration lors de la première initialisation de PostgreSQL.

## Modèle relationnel

- `utilisateurs`: identité, e-mail unique, téléphone facultatif unique, hash Argon2id, rôle (`client`, `livreur`, `administrateur`), état actif et date de création.
- `colis`: référence unique, client propriétaire, description, poids strictement positif, adresses, statut et date de création.
- `livraisons`: colis, livreur facultatif, statut, dates et commentaire.

Les clés étrangères empêchent de supprimer un client qui possède des colis (`RESTRICT`) et préservent l'historique si un livreur est supprimé (`SET NULL`). Les identifiants sont des UUID; les statuts et rôles sont des ENUM PostgreSQL.

## API

| Méthode | Route | Accès | Fonction |
|---|---|---|---|
| GET | `/health` | Public | Vérifie que le service et sa base répondent |
| POST | `/auth/register` | Public | Inscrit un client; son rôle est attribué par le serveur |
| POST | `/auth/login` | Public | Vérifie le mot de passe et renvoie un JWT |
| GET | `/auth/me` | JWT | Renvoie le profil connecté |
| POST | `/auth/verify` | JWT | Vérifie le jeton pour les autres services |
| GET | `/users` | Administrateur | Liste les utilisateurs |
| PATCH | `/users/{user_id}/role` | Administrateur | Modifie le rôle |
| GET | `/internal/validate` | JWT | Fournit l'identité et le rôle aux services internes |

Les mots de passe sont hachés avec Argon2id. Les JWT HS256 portent `sub`, `role`, `email`, `iat` et `exp`; transmettez-les avec `Authorization: Bearer <token>`. En production, définir un `JWT_SECRET` aléatoire et le partager uniquement entre les services backend.

Les comptes de démonstration créés par `database/init.sql` utilisent le mot de passe `Demo1234!`. Ils sont réservés au développement et ne doivent pas être gardés en production.

## Lancement et tests

À la racine du dépôt, `docker compose up --build` lance la base et l'API. En local, depuis `services/utilisateurs`, installer `requirements.txt`, définir `DATABASE_URL` et `JWT_SECRET`, puis lancer `uvicorn main:app --reload --port 8000`.

Les tests se lancent depuis `services/utilisateurs` avec `python -m pytest`. `pytest.ini` impose un minimum de 60 % de couverture.
