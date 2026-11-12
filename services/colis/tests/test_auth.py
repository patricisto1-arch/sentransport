import jwt


def test_token_absent(client):
    assert client.get("/").status_code == 401


def test_format_bearer_invalide(client):
    assert client.get("/", headers={"Authorization": "Basic abc"}).status_code == 401


def test_token_valide(client, headers):
    assert client.get("/", headers=headers()).status_code == 200


def test_role_inconnu_refuse(client, token):
    bad = token(role="administrateur")
    response = client.get("/", headers={"Authorization": f"Bearer {bad}"})
    assert response.status_code == 401


def test_sub_non_numerique_refuse(client, token):
    bad = token(user_id="not-an-integer")
    response = client.get("/", headers={"Authorization": f"Bearer {bad}"})
    assert response.status_code == 401


def test_token_expire_refuse(client):
    # exp volontairement dans le passe
    expired = jwt.encode({"sub": "1", "role": "client", "exp": 1}, "senTransport-test-secret-key-32-bytes-minimum", algorithm="HS256")
    response = client.get("/", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
