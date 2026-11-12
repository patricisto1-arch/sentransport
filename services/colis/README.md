# SenTransport - Service Colis

Service FastAPI conforme a `docs/contrats-api.md` et au schema `database/init.sql`.

## Variables d'environnement

- `DATABASE_URL` : connexion PostgreSQL partagee.
- `JWT_SECRET` : secret HS256 partage avec le service Utilisateurs.

Avec Docker Compose, placer un fichier `.env` a la racine du projet (au meme niveau que `docker-compose.yml`) : Compose le charge automatiquement. Pour lancer Uvicorn directement depuis le terminal, definir `DATABASE_URL` et `JWT_SECRET` dans les variables d’environnement de ce terminal. Ne jamais committer le vrai `.env`.

## Lancement local

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Le service ne cree ni ne modifie le schema : `database/init.sql` est execute par l'initialisation PostgreSQL.

## Tests

```bash
pytest -q
```

Les tests utilisent une base SQLite en memoire et remplacent la dependance de session. Une verification d'integration avec PostgreSQL 16 reste necessaire avant le merge.
