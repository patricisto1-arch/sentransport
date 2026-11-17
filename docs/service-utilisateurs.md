# Service Utilisateurs et socle de données — SenTransport

Ce document suit le contrat partagé de l'équipe (`docs/contrats-api.md`). Le service FastAPI est dans `services/utilisateurs/main.py`; le schéma PostgreSQL et les données de démonstration sont dans `database/init.sql`.

## Données

- `utilisateurs`: id `SERIAL`, nom, e-mail unique, hash Argon2id du mot de passe, rôle (`client`, `livreur`, `admin`) et date de création.
- `colis`: id `SERIAL`, expéditeur lié à `utilisateurs`, identité et adresse du destinataire, description facultative, poids positif, statut et date de création.
- `livraisons`: id `SERIAL`, colis unique lié à `colis`, livreur lié à `utilisateurs`, statut et dates de création/mise à jour.
- `historique_livraisons`: changements de statut liés à `livraisons`.

Les contraintes SQL contrôlent les rôles, statuts et poids. Les suppressions d'expéditeurs, livreurs et colis référencés sont restreintes; la suppression d'une livraison conserve les contraintes de cohérence en supprimant son historique associé.

## API Utilisateurs

Le proxy Nginx retire `/api/utilisateurs` : le service reçoit les chemins suivants.

| Méthode | Chemin interne | Accès | Résultat |
|---|---|---|---|
| GET | `/health` | Public | `{"status":"ok","service":"utilisateurs"}` |
| POST | `/auth/register` | Public | Création d'un compte client (`201`) |
| POST | `/auth/login` | Public | Jeton d'accès et type bearer |
| GET | `/me` | JWT | Profil connecté |
| GET | `/livreurs` | Administrateur | Liste des livreurs |

Les inscriptions publiques sont limitées au rôle `client`. Les comptes de démonstration fournissent un livreur et un administrateur pour les tests. Inscription et profil renvoient uniquement `id`, `nom`, `email`, `role`, jamais le hash du mot de passe.
Les erreurs de validation de requête utilisent le code `400`, conformément aux contrats partagés.

## JWT et mots de passe

Les mots de passe sont hachés avec Argon2id. Les jetons sont signés en HS256 avec `JWT_SECRET`, expirent au bout d'une heure et contiennent `sub`, `role` et `exp`. Chaque service consommateur doit vérifier localement la signature avec le même secret; aucun appel au service Utilisateurs n'est requis.

Le script SQL crée trois comptes de démonstration (`client.demo@…`, `livreur.demo@…`, `admin.demo@…`) avec le mot de passe `Demo1234!`. Utiliser ces comptes uniquement en développement et remplacer leurs identifiants en production.

## Lancement

La base partagée exécute `database/init.sql` au premier démarrage via Docker Compose. Le service écoute sur le port `8000`. Depuis `services/utilisateurs`, lancer `uvicorn main:app --host 0.0.0.0 --port 8000` après installation de `requirements.txt` et configuration de `DATABASE_URL` et `JWT_SECRET`.

Lancer les tests depuis `services/utilisateurs` avec `python -m pytest`. Le seuil de couverture est fixé à 60 % dans `pytest.ini`.
