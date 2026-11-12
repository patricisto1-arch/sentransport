
-- =====================================================
-- SENTRANSPORT - INITIALISATION DE LA BASE DE DONNEES
-- Schema aligne sur docs/contrats-api.md (section 7)
-- PostgreSQL 16
-- =====================================================

-- 1. TABLE UTILISATEURS
CREATE TABLE IF NOT EXISTS utilisateurs (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    mot_de_passe_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL
        CHECK (role IN ('client', 'livreur', 'admin')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABLE COLIS
CREATE TABLE IF NOT EXISTS colis (
    id SERIAL PRIMARY KEY,
    expediteur_id INTEGER NOT NULL,
    destinataire_nom VARCHAR(100) NOT NULL,
    destinataire_adresse VARCHAR(255) NOT NULL,
    description TEXT,
    poids_kg NUMERIC(6, 2) NOT NULL CHECK (poids_kg > 0),
    statut VARCHAR(20) NOT NULL DEFAULT 'en_attente'
        CHECK (statut IN ('en_attente', 'en_transit', 'livre', 'echec')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_colis_expediteur
        FOREIGN KEY (expediteur_id)
        REFERENCES utilisateurs(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 3. TABLE LIVRAISONS
-- Une seule livraison autorisee par colis
CREATE TABLE IF NOT EXISTS livraisons (
    id SERIAL PRIMARY KEY,
    colis_id INTEGER NOT NULL UNIQUE,
    livreur_id INTEGER NOT NULL,
    statut VARCHAR(20) NOT NULL DEFAULT 'en_attente'
        CHECK (statut IN ('en_attente', 'en_transit', 'livre', 'echec')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_livraison_colis
        FOREIGN KEY (colis_id)
        REFERENCES colis(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_livraison_livreur
        FOREIGN KEY (livreur_id)
        REFERENCES utilisateurs(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 4. TABLE HISTORIQUE_LIVRAISONS
CREATE TABLE IF NOT EXISTS historique_livraisons (
    id SERIAL PRIMARY KEY,
    livraison_id INTEGER NOT NULL,
    statut VARCHAR(20) NOT NULL
        CHECK (statut IN ('en_attente', 'en_transit', 'livre', 'echec')),
    date_changement TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_historique_livraison
        FOREIGN KEY (livraison_id)
        REFERENCES livraisons(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- 5. INDEX
CREATE INDEX IF NOT EXISTS idx_colis_expediteur_id
    ON colis(expediteur_id);

CREATE INDEX IF NOT EXISTS idx_colis_statut
    ON colis(statut);

CREATE INDEX IF NOT EXISTS idx_livraisons_livreur_id
    ON livraisons(livreur_id);

CREATE INDEX IF NOT EXISTS idx_livraisons_statut
    ON livraisons(statut);

CREATE INDEX IF NOT EXISTS idx_historique_livraison_id
    ON historique_livraisons(livraison_id);

CREATE INDEX IF NOT EXISTS idx_historique_date_changement
    ON historique_livraisons(date_changement);

-- 6. VERIFICATION DES TABLES
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'utilisateurs',
      'colis',
      'livraisons',
      'historique_livraisons'
  )
ORDER BY table_name;
