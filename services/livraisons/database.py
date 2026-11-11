"""Accès PostgreSQL du service Livraisons (tables livraisons et historique_livraisons)."""
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor


class DejaAffecte(Exception):
    """Le colis est déjà affecté à une livraison."""


@contextmanager
def get_cursor():
    """Ouvre une connexion, valide en cas de succès, annule en cas d'erreur."""
    conn = psycopg2.connect(os.getenv("DATABASE_URL", ""))
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def creer_livraison(colis_id: int, livreur_id: int) -> dict:
    """Crée la livraison (statut en_attente) et sa première ligne d'historique."""
    with get_cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO livraisons (colis_id, livreur_id, statut) "
                "VALUES (%s, %s, 'en_attente') RETURNING *",
                (colis_id, livreur_id),
            )
        except UniqueViolation:
            raise DejaAffecte(colis_id)
        livraison = cur.fetchone()
        cur.execute(
            "INSERT INTO historique_livraisons (livraison_id, statut) VALUES (%s, %s)",
            (livraison["id"], "en_attente"),
        )
        return livraison


def get_livraison(livraison_id: int) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM livraisons WHERE id = %s", (livraison_id,))
        return cur.fetchone()


def lister_livraisons(livreur_id: int | None = None, statut: str | None = None) -> list:
    """Liste les livraisons, avec filtres facultatifs."""
    sql = "SELECT * FROM livraisons WHERE 1=1"
    params = []
    if livreur_id is not None:
        sql += " AND livreur_id = %s"
        params.append(livreur_id)
    if statut is not None:
        sql += " AND statut = %s"
        params.append(statut)
    sql += " ORDER BY id"
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def changer_statut(livraison_id: int, statut: str) -> dict | None:
    """Met à jour le statut et l'historique dans la même transaction."""
    with get_cursor() as cur:
        cur.execute(
            "UPDATE livraisons SET statut = %s, updated_at = NOW() "
            "WHERE id = %s RETURNING *",
            (statut, livraison_id),
        )
        livraison = cur.fetchone()
        if livraison is None:
            return None
        cur.execute(
            "INSERT INTO historique_livraisons (livraison_id, statut) VALUES (%s, %s)",
            (livraison_id, statut),
        )
        return livraison


def get_historique(livraison_id: int) -> list:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM historique_livraisons WHERE livraison_id = %s "
            "ORDER BY date_changement, id",
            (livraison_id,),
        )
        return cur.fetchall()
