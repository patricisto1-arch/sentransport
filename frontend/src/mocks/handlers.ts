import { delay, http, HttpResponse } from 'msw';
import type { Colis, Livraison, StatutColis, Utilisateur } from '@/api/types';
import {
  type ColisDTO,
  type HistoriqueDTO,
  type JetonDTO,
  type LivraisonDTO,
  type MajColisDTO,
  type StatutContrat,
  type UtilisateurDTO,
  idDepuisNumero,
  numeroDepuisId,
  statutVersContrat,
  versColisDTO,
  versUtilisateurDTO,
  villeDepuisAdresse,
} from '@/api/contrat';
import { distanceEntre } from '@/lib/constants';
import { COLIS, LIVRAISONS, MOT_DE_PASSE_DEMO, UTILISATEURS } from './data';

let colisDb: Colis[] = structuredClone(COLIS);
let livraisonsDb: Livraison[] = structuredClone(LIVRAISONS);
let utilisateursDb: Utilisateur[] = structuredClone(UTILISATEURS);

export function reinitialiserBaseMock() {
  colisDb = structuredClone(COLIS);
  livraisonsDb = structuredClone(LIVRAISONS);
  utilisateursDb = structuredClone(UTILISATEURS);
}

const LATENCE_MUTATION = 380;

function erreur(detail: string, status = 400) {
  return HttpResponse.json({ detail }, { status });
}

function identifiantNumerique(valeur: string) {
  return Number(valeur.replace(/\D/g, '')) || 1;
}

function tokenPour(utilisateur: Utilisateur) {
  return `mock.${utilisateur.id}.${Date.now().toString(36)}`;
}

function utilisateurDuToken(request: Request): Utilisateur | null {
  const entete = request.headers.get('Authorization');
  if (!entete?.startsWith('Bearer ')) return null;
  const [prefixe, sub] = entete.slice('Bearer '.length).split('.');
  if (prefixe !== 'mock' || !sub) return null;
  return (
    utilisateursDb.find(
      (u) => identifiantNumerique(u.id) === identifiantNumerique(sub),
    ) ?? null
  );
}

const authRequise = () => erreur('Authentification requise.', 401);
const droitsInsuffisants = () => erreur('Droits insuffisants.', 403);

function utilisateurDTO(utilisateur: Utilisateur): UtilisateurDTO {
  return versUtilisateurDTO(utilisateur);
}

function colisDTO(colis: Colis): ColisDTO {
  return versColisDTO(colis);
}

function trouverColis(id: string): Colis | undefined {
  return colisDb.find(
    (c) => c.id === id || idDepuisNumero(c.numeroSuivi) === String(Number(id)),
  );
}

function livraisonDTO(livraison: Livraison): LivraisonDTO {
  const colis = trouverColis(livraison.colisId);
  return {
    id: identifiantNumerique(livraison.id),
    colis_id: colis
      ? Number(idDepuisNumero(colis.numeroSuivi))
      : identifiantNumerique(livraison.colisId),
    livreur_id: identifiantNumerique(livraison.livreurId),
    statut: statutVersContrat(livraison.statut),
    created_at: livraison.dateAffectation,
    updated_at: livraison.dateLivraison ?? livraison.dateAffectation,
  };
}

function historiqueDTO(livraison: Livraison): HistoriqueDTO[] {
  const colis = trouverColis(livraison.colisId);
  if (!colis) return [];
  return colis.historique.map((evenement, index) => ({
    id: index + 1,
    livraison_id: identifiantNumerique(livraison.id),
    statut: statutVersContrat(evenement.statut),
    date_changement: evenement.date,
  }));
}

function colisVisibles(utilisateur: Utilisateur) {
  if (utilisateur.role === 'administrateur') return colisDb;
  if (utilisateur.role === 'livreur') {
    const ids = new Set(
      livraisonsDb
        .filter((l) => l.livreurId === utilisateur.id)
        .map((l) => l.colisId),
    );
    return colisDb.filter(
      (c) => c.livreurId === utilisateur.id || ids.has(c.id),
    );
  }
  return colisDb.filter((c) => c.clientId === utilisateur.id);
}

function livraisonVisible(livraison: Livraison, utilisateur: Utilisateur) {
  if (utilisateur.role === 'administrateur') return true;
  if (utilisateur.role === 'livreur') return livraison.livreurId === utilisateur.id;
  const colis = trouverColis(livraison.colisId);
  return colis?.clientId === utilisateur.id;
}

function prochainIdentifiantColis() {
  const maximum = colisDb.reduce(
    (max, colis) => Math.max(max, Number(idDepuisNumero(colis.numeroSuivi))),
    0,
  );
  return maximum + 1;
}

function ajouterHistorique(colis: Colis, statut: StatutColis, libelle: string) {
  colis.historique = [
    ...colis.historique,
    {
      id: `${colis.id}-${colis.historique.length + 1}`,
      statut,
      libelle,
      lieu: colis.villeArrivee,
      date: new Date().toISOString(),
      acteur: 'SenTransport',
    },
  ];
}

export const handlers = [
  /* ----------------------------- Utilisateurs ---------------------------- */
  http.post('/api/utilisateurs/auth/login', async ({ request }) => {
    await delay(LATENCE_MUTATION);
    const { email, mot_de_passe } = (await request.json()) as {
      email: string;
      mot_de_passe: string;
    };
    const utilisateur = utilisateursDb.find(
      (u) => u.email.toLowerCase() === email.trim().toLowerCase(),
    );
    if (!utilisateur || mot_de_passe !== MOT_DE_PASSE_DEMO) {
      return erreur('E-mail ou mot de passe incorrect.', 401);
    }
    if (!utilisateur.actif) {
      return erreur('Ce compte a été désactivé.', 403);
    }
    return HttpResponse.json({
      access_token: tokenPour(utilisateur),
      token_type: 'bearer',
    } satisfies JetonDTO);
  }),

  http.post('/api/utilisateurs/auth/register', async ({ request }) => {
    await delay(LATENCE_MUTATION);
    const { nom, email, role } = (await request.json()) as {
      nom: string;
      email: string;
      mot_de_passe: string;
      role: 'client' | 'livreur';
    };
    if (!nom?.trim() || !email?.trim()) return erreur('Champs obligatoires manquants.');
    if (utilisateursDb.some((u) => u.email.toLowerCase() === email.toLowerCase())) {
      return erreur('Cet e-mail est déjà utilisé.', 409);
    }
    const morceaux = nom.trim().split(/\s+/);
    const prenom = morceaux.shift() ?? nom;
    const identifiant = Math.max(...utilisateursDb.map((u) => identifiantNumerique(u.id))) + 1;
    const utilisateur: Utilisateur = {
      id: String(identifiant),
      prenom,
      nom: morceaux.join(' ') || prenom,
      email,
      telephone: '',
      role: role === 'livreur' ? 'livreur' : 'client',
      ville: 'Dakar',
      actif: true,
      createdAt: new Date().toISOString(),
    };
    utilisateursDb = [...utilisateursDb, utilisateur];
    return HttpResponse.json(utilisateurDTO(utilisateur), { status: 201 });
  }),

  http.get('/api/utilisateurs/me', ({ request }) => {
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    return HttpResponse.json(utilisateurDTO(utilisateur));
  }),

  http.get('/api/utilisateurs/livreurs', ({ request }) => {
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    if (utilisateur.role !== 'administrateur') return droitsInsuffisants();
    return HttpResponse.json(
      utilisateursDb.filter((u) => u.role === 'livreur').map(utilisateurDTO),
    );
  }),

  /* -------------------------------- Colis -------------------------------- */
  http.get('/api/colis/', ({ request }) => {
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    return HttpResponse.json(colisVisibles(utilisateur).map(colisDTO));
  }),

  http.get('/api/colis/:id', ({ request, params }) => {
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    const colis = trouverColis(String(params.id));
    if (!colis) return erreur('Colis introuvable.', 404);
    if (!colisVisibles(utilisateur).some((c) => c.id === colis.id)) {
      return droitsInsuffisants();
    }
    return HttpResponse.json(colisDTO(colis));
  }),

  http.post('/api/colis/', async ({ request }) => {
    await delay(LATENCE_MUTATION);
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    if (!['client', 'administrateur'].includes(utilisateur.role)) {
      return droitsInsuffisants();
    }
    const corps = (await request.json()) as {
      destinataire_nom: string;
      destinataire_adresse: string;
      description: string;
      poids_kg: number;
    };
    if (!corps.destinataire_nom || !corps.destinataire_adresse) {
      return erreur('Destinataire incomplet.');
    }
    const identifiant = prochainIdentifiantColis();
    const villeArrivee = villeDepuisAdresse(corps.destinataire_adresse);
    const dateCreation = new Date().toISOString();
    const colis: Colis = {
      id: `c${identifiant}`,
      numeroSuivi: numeroDepuisId(identifiant, dateCreation),
      clientId: utilisateur.id,
      expediteur: {
        nom: `${utilisateur.prenom} ${utilisateur.nom}`.trim(),
        telephone: utilisateur.telephone,
        adresse: utilisateur.ville,
        ville: utilisateur.ville,
      },
      destinataire: {
        nom: corps.destinataire_nom,
        telephone: '',
        adresse: corps.destinataire_adresse,
        ville: villeArrivee,
      },
      description: corps.description ?? '',
      poidsKg: Number(corps.poids_kg) || 1,
      statut: 'en_attente',
      villeDepart: utilisateur.ville,
      villeArrivee,
      distanceKm: distanceEntre(utilisateur.ville, villeArrivee),
      dateCreation,
      dateLivraisonPrevue: new Date(Date.now() + 48 * 3600_000).toISOString(),
      prixFcfa:
        1500 +
        Math.round((Number(corps.poids_kg) || 1) * 450) +
        distanceEntre(utilisateur.ville, villeArrivee) * 12,
      historique: [
        {
          id: `${identifiant}-creation`,
          statut: 'en_attente',
          libelle: 'Colis enregistré',
          lieu: utilisateur.ville,
          date: dateCreation,
          acteur: 'Guichet SenTransport',
        },
      ],
    };
    colisDb = [colis, ...colisDb];
    return HttpResponse.json(colisDTO(colis), { status: 201 });
  }),

  http.put('/api/colis/:id', async ({ request, params }) => {
    await delay(LATENCE_MUTATION);
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    const colis = trouverColis(String(params.id));
    if (!colis) return erreur('Colis introuvable.', 404);
    const proprietaire = colis.clientId === utilisateur.id;
    if (!proprietaire && utilisateur.role !== 'administrateur') {
      return droitsInsuffisants();
    }
    if (colis.statut !== 'en_attente') {
      return erreur('Un colis déjà pris en charge ne peut plus être modifié.', 400);
    }
    const corps = (await request.json()) as MajColisDTO;
    if (corps.description !== undefined) colis.description = corps.description;
    if (corps.poids_kg !== undefined) {
      colis.poidsKg = Number(corps.poids_kg);
      colis.prixFcfa =
        1500 + Math.round(colis.poidsKg * 450) + colis.distanceKm * 12;
    }
    if (corps.destinataire_nom) colis.destinataire.nom = corps.destinataire_nom;
    if (corps.destinataire_adresse) {
      colis.destinataire.adresse = corps.destinataire_adresse;
      colis.destinataire.ville = villeDepuisAdresse(corps.destinataire_adresse);
      colis.villeArrivee = colis.destinataire.ville;
    }
    return HttpResponse.json(colisDTO(colis));
  }),

  http.delete('/api/colis/:id', ({ request, params }) => {
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    if (utilisateur.role !== 'administrateur') return droitsInsuffisants();
    const colis = trouverColis(String(params.id));
    if (!colis) return erreur('Colis introuvable.', 404);
    colisDb = colisDb.filter((c) => c.id !== colis.id);
    livraisonsDb = livraisonsDb.filter((l) => l.colisId !== colis.id);
    return new HttpResponse(null, { status: 204 });
  }),

  http.patch('/api/colis/:id/statut', async ({ request, params }) => {
    await delay(LATENCE_MUTATION);
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    if (!['livreur', 'administrateur'].includes(utilisateur.role)) {
      return droitsInsuffisants();
    }
    const colis = trouverColis(String(params.id));
    if (!colis) return erreur('Colis introuvable.', 404);
    const { statut } = (await request.json()) as { statut: StatutContrat };
    if (!['en_attente', 'en_transit', 'livre', 'echec'].includes(statut)) {
      return erreur('Statut invalide.');
    }
    colis.statut = statut;
    ajouterHistorique(colis, statut, `Statut mis à jour : ${statut}`);
    return HttpResponse.json(colisDTO(colis));
  }),

  /* ------------------------------ Livraisons ----------------------------- */
  http.get('/api/livraisons/', ({ request }) => {
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    const url = new URL(request.url);
    const livreurId = url.searchParams.get('livreur_id');
    const statut = url.searchParams.get('statut');
    const liste = livraisonsDb.filter((livraison) => {
      if (!livraisonVisible(livraison, utilisateur)) return false;
      if (livreurId && identifiantNumerique(livraison.livreurId) !== Number(livreurId)) {
        return false;
      }
      if (statut && statutVersContrat(livraison.statut) !== statut) return false;
      return true;
    });
    return HttpResponse.json(liste.map(livraisonDTO));
  }),

  http.get('/api/livraisons/:id', ({ request, params }) => {
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    const livraison = livraisonsDb.find(
      (l) => identifiantNumerique(l.id) === Number(params.id),
    );
    if (!livraison) return erreur('Livraison introuvable.', 404);
    if (!livraisonVisible(livraison, utilisateur)) return droitsInsuffisants();
    return HttpResponse.json(livraisonDTO(livraison));
  }),

  http.get('/api/livraisons/:id/historique', ({ request, params }) => {
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    const livraison = livraisonsDb.find(
      (l) => identifiantNumerique(l.id) === Number(params.id),
    );
    if (!livraison) return erreur('Livraison introuvable.', 404);
    if (!livraisonVisible(livraison, utilisateur)) return droitsInsuffisants();
    return HttpResponse.json(historiqueDTO(livraison));
  }),

  http.post('/api/livraisons/', async ({ request }) => {
    await delay(LATENCE_MUTATION);
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    if (utilisateur.role !== 'administrateur') return droitsInsuffisants();
    const { colis_id, livreur_id } = (await request.json()) as {
      colis_id: number;
      livreur_id: number;
    };
    const colis = trouverColis(String(colis_id));
    const livreur = utilisateursDb.find(
      (u) => identifiantNumerique(u.id) === Number(livreur_id) && u.role === 'livreur',
    );
    if (!colis) return erreur('Colis introuvable.', 404);
    if (!livreur) return erreur('Livreur introuvable.', 404);
    if (livraisonsDb.some((l) => l.colisId === colis.id)) {
      return erreur('Ce colis a déjà une livraison.', 409);
    }
    const maintenant = new Date().toISOString();
    const livraison: Livraison = {
      id: `l${Math.max(0, ...livraisonsDb.map((l) => identifiantNumerique(l.id))) + 1}`,
      colisId: colis.id,
      numeroSuivi: colis.numeroSuivi,
      livreurId: livreur.id,
      statut: 'en_attente',
      dateAffectation: maintenant,
      tournee: 'Tournée affectée',
    };
    livraisonsDb = [livraison, ...livraisonsDb];
    colis.livreurId = livreur.id;
    return HttpResponse.json(livraisonDTO(livraison), { status: 201 });
  }),

  http.patch('/api/livraisons/:id/statut', async ({ request, params }) => {
    await delay(LATENCE_MUTATION);
    const utilisateur = utilisateurDuToken(request);
    if (!utilisateur) return authRequise();
    const livraison = livraisonsDb.find(
      (l) => identifiantNumerique(l.id) === Number(params.id),
    );
    if (!livraison) return erreur('Livraison introuvable.', 404);
    if (
      utilisateur.role !== 'administrateur' &&
      livraison.livreurId !== utilisateur.id
    ) {
      return droitsInsuffisants();
    }
    const { statut } = (await request.json()) as { statut: StatutContrat };
    if (!['en_attente', 'en_transit', 'livre', 'echec'].includes(statut)) {
      return erreur('Statut invalide.');
    }
    livraison.statut = statut;
    if (statut === 'livre') {
      livraison.dateLivraison = new Date().toISOString();
    }
    const colis = trouverColis(livraison.colisId);
    if (colis) {
      colis.statut = statut;
      if (statut === 'livre') colis.dateLivraison = livraison.dateLivraison;
      ajouterHistorique(colis, statut, `Statut mis à jour : ${statut}`);
    }
    return HttpResponse.json(livraisonDTO(livraison));
  }),
];