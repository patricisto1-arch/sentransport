# Guide de déploiement

Ce guide explique comment mettre SenTransport en ligne sur un serveur, avec le workflow GitHub Actions (`.github/workflows/ci-cd.yml`).

## Comment ça marche

À chaque push sur `develop` ou `main`, une fois les tests passés et les images publiées dans `ghcr.io`, le job `deploy` :

1. se connecte au serveur par **SSH** avec l'utilisateur `deploy` ;
2. copie sur le serveur `docker-compose.yml`, `gateway/` et `database/` ;
3. écrit un fichier `.env` avec le préfixe des images, le SHA du commit et les secrets ;
4. se connecte à `ghcr.io`, télécharge les images (`docker compose pull`) et relance les conteneurs (`docker compose up -d`).

| Branche | Environnement | Déclenchement |
|---|---|---|
| `develop` | `staging` | automatique |
| `main` | `production` | automatique, ou après validation d'un relecteur si l'environnement l'exige |

## 1. Préparer le serveur

Il faut un serveur Linux (Ubuntu 22.04 ou plus récent) avec une adresse IP publique, le **port 80 ouvert** et un accès administrateur. Un serveur par environnement est idéal ; un seul peut servir pour une démonstration.

**Installer Docker :**

```bash
curl -fsSL https://get.docker.com | sudo sh
```

**Créer l'utilisateur de déploiement**, autorisé à lancer Docker :

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
```

## 2. Créer la clé SSH du workflow

Sur **votre machine** (pas sur le serveur) :

```powershell
ssh-keygen -t ed25519 -C "github-actions-sentransport" -f sentransport_deploy
```

Laissez la phrase secrète vide. Deux fichiers sont créés :

- `sentransport_deploy.pub` : la clé **publique**, à installer sur le serveur ;
- `sentransport_deploy` : la clé **privée**, à mettre dans les secrets GitHub. Ne l'envoyez jamais à personne et ne la commitez jamais.

**Installer la clé publique sur le serveur**, en tant que `deploy` :

```bash
sudo -u deploy mkdir -p /home/deploy/.ssh
echo "<contenu de sentransport_deploy.pub>" | sudo -u deploy tee -a /home/deploy/.ssh/authorized_keys
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

**Tester la connexion** depuis votre machine :

```powershell
ssh -i sentransport_deploy deploy@<adresse-du-serveur> "docker ps"
```

La commande doit répondre sans demander de mot de passe.

## 3. Déclarer les secrets sur GitHub

### Secrets du dépôt

*Settings → Secrets and variables → Actions → New repository secret* :

| Nom | Valeur |
|---|---|
| `SSH_PRIVATE_KEY` | tout le contenu du fichier `sentransport_deploy` (lignes `BEGIN` et `END` comprises) |
| `POSTGRES_PASSWORD` | un mot de passe long et aléatoire |
| `JWT_SECRET` | une chaîne aléatoire d'au moins 32 caractères |

Pour générer une valeur aléatoire :

```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 40 | ForEach-Object { [char]$_ })
```

Utilisez des valeurs **différentes de celles des tests locaux**.

### Environnements

*Settings → Environments → New environment* : créez `staging` et `production`. Dans **chacun**, ajoutez un secret :

| Nom | Valeur |
|---|---|
| `DEPLOY_HOST` | adresse IP ou nom de domaine du serveur de cet environnement |

Dans `production`, activez **Required reviewers** et choisissez un relecteur : le déploiement attend alors sa validation. Cette protection n'est disponible que si le dépôt est public ou si le compte a un abonnement payant.

## 4. Déployer

Un push sur `develop` lance le déploiement `staging`, un push sur `main` celui de `production`. Suivez-le dans l'onglet **Actions**.

Au premier déploiement, la base est créée et `database/init.sql` est exécuté.

## 5. Vérifier

Sur le serveur, en tant que `deploy` :

```bash
cd ~/sentransport
docker compose ps
```

Les services `db`, `colis`, `utilisateurs`, `livraisons` et `frontend` doivent être `healthy`. Depuis votre machine :

```powershell
curl.exe http://<adresse-du-serveur>/api/colis/health
curl.exe http://<adresse-du-serveur>/api/utilisateurs/health
curl.exe http://<adresse-du-serveur>/api/livraisons/health
```

Chaque appel renvoie `{"status":"ok",...}`. Ouvrez ensuite `http://<adresse-du-serveur>/` et connectez-vous avec un compte de démonstration.

## 6. Retour en arrière

Chaque image est publiée avec le SHA du commit. Pour revenir à une version précédente, sur le serveur :

```bash
cd ~/sentransport
nano .env          # remplacer la valeur de TAG par le SHA de l'ancienne version
docker compose pull
docker compose up -d
```

Vous pouvez aussi faire un `git revert` du commit fautif puis pousser : le workflow redéploie l'état précédent.

## 7. Points d'attention

- **`init.sql` ne s'exécute qu'une fois**, quand la base est créée. Modifier le fichier n'a aucun effet sur une base existante. Pour repartir de zéro (les données sont perdues) : `docker compose down -v` sur le serveur, puis relancer un déploiement.
- **Comptes de démonstration** : `init.sql` crée trois comptes dont le mot de passe est public. En production réelle, supprimez-les ou changez leur mot de passe.
- **HTTPS** : la configuration actuelle sert l'application en HTTP. Pour un usage réel, ajoutez un certificat (par exemple Let's Encrypt avec Certbot ou Caddy) devant la passerelle.
- **Images privées** : les images d'un dépôt privé sont privées dans `ghcr.io` ; le workflow se connecte avec le jeton `GITHUB_TOKEN` le temps du déploiement. Les conteneurs déjà téléchargés continuent de tourner après.
- **Pare-feu** : n'ouvrez que les ports 22 (SSH) et 80 (HTTP, et 443 avec HTTPS). La base PostgreSQL n'est pas exposée à l'extérieur.

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Le job `deploy` échoue à « Préparer SSH » | `SSH_PRIVATE_KEY` ou `DEPLOY_HOST` vide ou incorrect | Vérifier les secrets du dépôt et de l'environnement |
| `Permission denied (publickey)` | La clé publique n'est pas dans `authorized_keys` de `deploy` | Refaire l'étape 2 |
| `permission denied` sur Docker | `deploy` n'est pas dans le groupe `docker` | `sudo usermod -aG docker deploy`, puis se reconnecter |
| `pull access denied` | Le paquet `ghcr.io` n'est pas accessible | Vérifier que `package` a réussi avant `deploy` |
| Services `unhealthy` ou qui redémarrent | Variable manquante ou base incompatible | `docker compose logs <service> --tail 50` |
| Connexion impossible sur la page | Port 80 fermé | Ouvrir le port 80 dans le pare-feu du serveur |
