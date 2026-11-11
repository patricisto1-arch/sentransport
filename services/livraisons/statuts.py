"""Règles de transition des statuts d'une livraison."""

STATUTS = ("en_attente", "en_transit", "livre", "echec")

TRANSITIONS = {
    "en_attente": {"en_transit", "echec"},
    "en_transit": {"livre", "echec"},
    "livre": set(),
    "echec": set(),
}


def transition_valide(actuel: str, nouveau: str) -> bool:
    """Retourne True si on peut passer du statut actuel au nouveau."""
    return nouveau in TRANSITIONS.get(actuel, set())
