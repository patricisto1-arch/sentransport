import httpx
import pytest

import colis_client


class FausseReponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data

    def json(self):
        if self._json is None:
            raise ValueError("pas de JSON")
        return self._json


def faux_get(reponse):
    def _get(url, headers=None, timeout=None):
        _get.appel = (url, headers)
        return reponse
    return _get


@pytest.fixture(autouse=True)
def url_colis(monkeypatch):
    monkeypatch.setenv("COLIS_URL", "http://colis:8000")


def test_colis_existe(monkeypatch):
    get = faux_get(FausseReponse(200, {"id": 12}))
    monkeypatch.setattr(colis_client.httpx, "get", get)
    assert colis_client.colis_existe(12, "tok") is True
    assert get.appel == ("http://colis:8000/12", {"Authorization": "Bearer tok"})


def test_colis_introuvable(monkeypatch):
    monkeypatch.setattr(colis_client.httpx, "get", faux_get(FausseReponse(404)))
    assert colis_client.colis_existe(99, "tok") is False


def test_colis_existe_erreur_serveur(monkeypatch):
    monkeypatch.setattr(colis_client.httpx, "get", faux_get(FausseReponse(500)))
    with pytest.raises(colis_client.ColisIndisponible):
        colis_client.colis_existe(12, "tok")


def test_colis_existe_refuse(monkeypatch):
    rep = FausseReponse(403, {"detail": "Accès interdit"})
    monkeypatch.setattr(colis_client.httpx, "get", faux_get(rep))
    with pytest.raises(colis_client.ColisRefuse) as e:
        colis_client.colis_existe(12, "tok")
    assert e.value.status_code == 403
    assert e.value.detail == "Accès interdit"


def test_colis_injoignable(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("injoignable")
    monkeypatch.setattr(colis_client.httpx, "get", boom)
    with pytest.raises(colis_client.ColisIndisponible):
        colis_client.colis_existe(12, "tok")


def test_maj_statut_ok(monkeypatch):
    appels = {}

    def faux_patch(url, json=None, headers=None, timeout=None):
        appels["args"] = (url, json, headers)
        return FausseReponse(200)

    monkeypatch.setattr(colis_client.httpx, "patch", faux_patch)
    colis_client.maj_statut_colis(12, "livre", "tok")
    assert appels["args"] == (
        "http://colis:8000/12/statut",
        {"statut": "livre"},
        {"Authorization": "Bearer tok"},
    )


def test_maj_statut_erreur_serveur(monkeypatch):
    monkeypatch.setattr(
        colis_client.httpx, "patch", lambda *a, **k: FausseReponse(503)
    )
    with pytest.raises(colis_client.ColisIndisponible):
        colis_client.maj_statut_colis(12, "livre", "tok")


def test_maj_statut_refuse_sans_json(monkeypatch):
    monkeypatch.setattr(
        colis_client.httpx, "patch", lambda *a, **k: FausseReponse(400)
    )
    with pytest.raises(colis_client.ColisRefuse) as e:
        colis_client.maj_statut_colis(12, "livre", "tok")
    assert e.value.detail == "Erreur du service Colis"


def test_maj_statut_injoignable(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("injoignable")
    monkeypatch.setattr(colis_client.httpx, "patch", boom)
    with pytest.raises(colis_client.ColisIndisponible):
        colis_client.maj_statut_colis(12, "livre", "tok")