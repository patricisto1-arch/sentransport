"""Appels HTTP vers le service Colis."""
import os

import httpx

TIMEOUT = 5.0


class ColisIndisponible(Exception):
    """Le service Colis ne répond pas ou renvoie une erreur serveur."""


class ColisRefuse(Exception):
    """Le service Colis a refusé la requête (droits, statut invalide...)."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _url() -> str:
    return os.getenv("COLIS_URL", "http://colis:8000")


def _detail(reponse: httpx.Response) -> str:
    try:
        return reponse.json().get("detail", "Erreur du service Colis")
    except ValueError:
        return "Erreur du service Colis"


def colis_existe(colis_id: int, token: str) -> bool:
    """True si le colis existe, False s'il est introuvable (404)."""
    try:
        r = httpx.get(
            f"{_url()}/{colis_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
    except httpx.HTTPError:
        raise ColisIndisponible()
    if r.status_code == 404:
        return False
    if r.status_code >= 500:
        raise ColisIndisponible()
    if r.status_code >= 400:
        raise ColisRefuse(r.status_code, _detail(r))
    return True


def maj_statut_colis(colis_id: int, statut: str, token: str) -> None:
    """Synchronise le statut du colis avec celui de la livraison."""
    try:
        r = httpx.patch(
            f"{_url()}/{colis_id}/statut",
            json={"statut": statut},
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
    except httpx.HTTPError:
        raise ColisIndisponible()
    if r.status_code >= 500:
        raise ColisIndisponible()
    if r.status_code >= 400:
        raise ColisRefuse(r.status_code, _detail(r))
