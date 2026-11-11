-- Schéma initial SenTransport (PostgreSQL 16). Exécuté automatiquement au premier démarrage.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN CREATE TYPE user_role AS ENUM ('client', 'livreur', 'administrateur'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE parcel_status AS ENUM ('en_attente', 'prise_en_charge', 'en_transit', 'livre', 'annule'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE delivery_status AS ENUM ('affectee', 'en_cours', 'terminee', 'echec'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS utilisateurs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom VARCHAR(120) NOT NULL CHECK (length(nom) >= 2),
    email VARCHAR(255) NOT NULL UNIQUE,
    telephone VARCHAR(30) UNIQUE,
    mot_de_passe_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'client',
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_utilisateurs_email ON utilisateurs(email);

CREATE TABLE IF NOT EXISTS colis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference VARCHAR(40) NOT NULL UNIQUE,
    client_id UUID NOT NULL REFERENCES utilisateurs(id) ON DELETE RESTRICT,
    description TEXT NOT NULL,
    poids_kg DOUBLE PRECISION NOT NULL CHECK (poids_kg > 0),
    adresse_depart VARCHAR(255) NOT NULL,
    adresse_arrivee VARCHAR(255) NOT NULL,
    statut parcel_status NOT NULL DEFAULT 'en_attente',
    cree_le TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_colis_reference ON colis(reference);
CREATE INDEX IF NOT EXISTS ix_colis_client_id ON colis(client_id);

CREATE TABLE IF NOT EXISTS livraisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    colis_id UUID NOT NULL REFERENCES colis(id) ON DELETE RESTRICT,
    livreur_id UUID REFERENCES utilisateurs(id) ON DELETE SET NULL,
    statut delivery_status NOT NULL DEFAULT 'affectee',
    date_affectation TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_livraison TIMESTAMPTZ,
    commentaire TEXT
);
CREATE INDEX IF NOT EXISTS ix_livraisons_colis_id ON livraisons(colis_id);
CREATE INDEX IF NOT EXISTS ix_livraisons_livreur_id ON livraisons(livreur_id);

-- Comptes de démonstration (mot de passe commun : Demo1234!).
-- Le hash Argon2id est volontairement un hash, jamais un mot de passe en clair.
INSERT INTO utilisateurs (nom, email, telephone, mot_de_passe_hash, role)
VALUES
 ('Client Démo', 'client.demo@sentransport.local', '+221770000001', '$argon2id$v=19$m=65536,t=3,p=4$sdOCCHkhMq50gML3IQzl4A$ZDqJP6VSQUPobypC8xfpLIpPKTw/sjCYw04onmexcgk', 'client'),
 ('Livreur Démo', 'livreur.demo@sentransport.local', '+221770000002', '$argon2id$v=19$m=65536,t=3,p=4$sdOCCHkhMq50gML3IQzl4A$ZDqJP6VSQUPobypC8xfpLIpPKTw/sjCYw04onmexcgk', 'livreur'),
 ('Administrateur Démo', 'admin.demo@sentransport.local', '+221770000003', '$argon2id$v=19$m=65536,t=3,p=4$sdOCCHkhMq50gML3IQzl4A$ZDqJP6VSQUPobypC8xfpLIpPKTw/sjCYw04onmexcgk', 'administrateur')
ON CONFLICT (email) DO NOTHING;

INSERT INTO colis (reference, client_id, description, poids_kg, adresse_depart, adresse_arrivee)
SELECT 'COLIS-DEMO-001', id, 'Documents de démonstration', 0.5, 'Dakar-Plateau', 'Almadies'
FROM utilisateurs WHERE email = 'client.demo@sentransport.local'
ON CONFLICT (reference) DO NOTHING;

INSERT INTO livraisons (colis_id, livreur_id, statut)
SELECT c.id, u.id, 'affectee'
FROM colis c CROSS JOIN utilisateurs u
WHERE c.reference = 'COLIS-DEMO-001' AND u.email = 'livreur.demo@sentransport.local'
AND NOT EXISTS (SELECT 1 FROM livraisons l WHERE l.colis_id = c.id);
