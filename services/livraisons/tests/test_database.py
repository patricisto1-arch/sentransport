from contextlib import contextmanager

import pytest
from psycopg2.errors import UniqueViolation

import database


class FauxCurseur:
    def __init__(self, un=None, tous=None, erreur=None):
        self.un, self.tous, self.erreur = un, tous or [], erreur
        self.requetes = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.requetes.append((sql, params))
        if self.erreur:
            raise self.erreur

    def fetchone(self):
        return self.un

    def fetchall(self):
        return self.tous


class FausseConnexion:
    def __init__(self, curseur):
        self.curseur = curseur
        self.valide = self.annule = self.ferme = False

    def cursor(self, cursor_factory=None):
        return self.curseur

    def commit(self):
        self.valide = True

    def rollback(self):
        self.annule = True

    def close(self):
        self.ferme = True


def brancher(monkeypatch, curseur):
    @contextmanager
    def faux():
        yield curseur

    monkeypatch.setattr(database, "get_cursor", faux)


def test_creer_livraison(monkeypatch):
    cur = FauxCurseur(un={"id": 7, "colis_id": 12, "livreur_id": 4})
    brancher(monkeypatch, cur)
    assert database.creer_livraison(12, 4)["id"] == 7
    assert len(cur.requetes) == 2
    assert "historique_livraisons" in cur.requetes[1][0]


def test_creer_livraison_deja_affecte(monkeypatch):
    brancher(monkeypatch, FauxCurseur(erreur=UniqueViolation()))
    with pytest.raises(database.DejaAffecte):
        database.creer_livraison(12, 4)


def test_get_livraison(monkeypatch):
    brancher(monkeypatch, FauxCurseur(un={"id": 7}))
    assert database.get_livraison(7) == {"id": 7}


def test_lister_sans_filtre(monkeypatch):
    cur = FauxCurseur(tous=[{"id": 1}])
    brancher(monkeypatch, cur)
    assert database.lister_livraisons() == [{"id": 1}]
    assert cur.requetes[0][1] == []


def test_lister_avec_filtres(monkeypatch):
    cur = FauxCurseur(tous=[])
    brancher(monkeypatch, cur)
    database.lister_livraisons(livreur_id=4, statut="livre")
    sql, params = cur.requetes[0]
    assert "livreur_id" in sql and "statut" in sql
    assert params == [4, "livre"]


def test_changer_statut(monkeypatch):
    cur = FauxCurseur(un={"id": 7, "statut": "livre"})
    brancher(monkeypatch, cur)
    assert database.changer_statut(7, "livre")["statut"] == "livre"
    assert len(cur.requetes) == 2


def test_changer_statut_introuvable(monkeypatch):
    cur = FauxCurseur(un=None)
    brancher(monkeypatch, cur)
    assert database.changer_statut(99, "livre") is None
    assert len(cur.requetes) == 1  # pas d'historique écrit


def test_get_historique(monkeypatch):
    brancher(monkeypatch, FauxCurseur(tous=[{"id": 1}, {"id": 2}]))
    assert len(database.get_historique(7)) == 2


def test_get_cursor_valide(monkeypatch):
    conn = FausseConnexion(FauxCurseur())
    monkeypatch.setattr(database.psycopg2, "connect", lambda url: conn)
    with database.get_cursor():
        pass
    assert conn.valide and not conn.annule and conn.ferme


def test_get_cursor_annule_sur_erreur(monkeypatch):
    conn = FausseConnexion(FauxCurseur())
    monkeypatch.setattr(database.psycopg2, "connect", lambda url: conn)
    with pytest.raises(RuntimeError):
        with database.get_cursor():
            raise RuntimeError("boom")
    assert conn.annule and not conn.valide and conn.ferme