from statuts import transition_valide


def test_transitions_autorisees():
    assert transition_valide("en_attente", "en_transit")
    assert transition_valide("en_transit", "livre")
    assert transition_valide("en_transit", "echec")


def test_transitions_interdites():
    assert not transition_valide("livre", "en_attente")
    assert not transition_valide("en_attente", "livre")
    assert not transition_valide("echec", "en_transit")


def test_statut_inconnu():
    assert not transition_valide("inconnu", "livre")