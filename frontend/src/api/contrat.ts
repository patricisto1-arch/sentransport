/**
 * Adaptateurs entre les contrats d'API de l'équipe (snake_case) et les modèles
 * d'affichage de l'interface (camelCase). Les pages ne connaissent que les
 * seconds ; toute la traduction réseau est centralisée ici.
 */
import type {
  Adresse,
  Colis,
  EvenementSuivi,
  Livraison,
  Role,
  StatutColis,
  Utilisateur,
} from './types';
import { distanceEntre, villeParNom } from '@/lib/constants';

export type RoleContrat = 'client' | 'livreur' | 'admin';
export type StatutContrat = 'en_attente' | 'en_transit' | 'livre' | 'echec';

export interface UtilisateurDTO {
  id: number;
  nom: string;
  email: string;
  role: RoleContrat;
}

export interface ColisDTO {
  id: number;
  expediteur_id: number;
  destinataire_nom: string;
  destinataire_adresse: string;
  description: string;
  poids_kg: number;
  statut: StatutContrat;
  created_at: string;
}

export interface LivraisonDTO {
  id: number;
  colis_id: number;
  livreur_id: number;
  statut: StatutContrat;
  created_at: string;
  updated_at: string;
}

export interface HistoriqueDTO {
  id: number;
  livraison_id: number;
  statut: StatutContrat;
  date_changement: string;
}

export interface ConnexionDTO {
  email: string;
  mot_de_passe: string;
}

export interface InscriptionDTO {
  nom: string;
  email: string;
  mot_de_passe: string;
  role: Exclude<RoleContrat, 'admin'>;
}

export interface JetonDTO {
  access_token: string;
  token_type: 'bearer';
}

export interface CreationColisDTO {
  destinataire_nom: string;
  destinataire_adresse: string;
  description: string;
  poids_kg: number;
}

export interface MajColisDTO {
  destinataire_nom?: string;
  destinataire_adresse?: string;
  description?: string;
  poids_kg?: number;
}

export interface AffectationDTO {
  colis_id: number;
  livreur_id: number;
}

const ROLE_VERS_INTERNE: Record<RoleContrat, Role> = {
  client: 'client',
  livreur: 'livreur',
  admin: 'administrateur',
};

export function roleDepuisContrat(role: RoleContrat): Role {
  return ROLE_VERS_INTERNE[role] ?? 'client';
}

export function roleVersContrat(role: Role): RoleContrat {
  return role === 'administrateur' ? 'admin' : role;
}

/** Les statuts `pris_en_charge` de la maquette n'existent pas côté API. */
export function statutDepuisContrat(statut: Statistique): StatutColis {
  return statut === 'pris_en_charge' ? 'en_transit' : statut;
}

type Statistique = StatutColis | StatutContrat;

export function statutVersContrat(statut: StatutColis): StatutContrat {
  return statut === 'pris_en_charge' ? 'en_transit' : statut;
}

export function idDepuisNumero(numero: string): string {
  const chiffres = numero.match(/(\d+)$/)?.[1];
  return chiffres ? String(Number(chiffres)) : numero;
}

export function numeroDepuisId(id: number | string, date: string | Date = new Date()): string {
  const annee = new Date(date).getFullYear();
  return `ST-${annee}-${String(id).padStart(5, '0')}`;
}

export function villeDepuisAdresse(adresse: string): string {
  const morceaux = adresse
    .split(',')
    .map((morceau) => morceau.trim())
    .filter(Boolean);
  return morceaux[morceaux.length - 1] ?? 'Dakar';
}

function nomComplet(nom: string) {
  const morceaux = nom.trim().split(/\s+/);
  const prenom = morceaux.shift() ?? nom;
  return { prenom, nom: morceaux.join(' ') || prenom };
}

export function versUtilisateur(dto: UtilisateurDTO): Utilisateur {
  const { prenom, nom } = nomComplet(dto.nom);
  return {
    id: String(dto.id),
    prenom,
    nom,
    email: dto.email,
    telephone: '',
    role: roleDepuisContrat(dto.role),
    ville: 'Dakar',
    actif: true,
    createdAt: new Date().toISOString(),
  };
}

export function versAdresse(
  nom: string,
  adresse: string,
  ville: string,
): Adresse {
  const centre = villeParNom(ville);
  return {
    nom,
    telephone: '',
    adresse,
    ville,
    coordonnees: centre ? { lat: centre.lat, lng: centre.lng } : undefined,
  };
}

export function versColis(
  dto: ColisDTO,
  options: { expediteur?: Utilisateur; historique?: EvenementSuivi[] } = {},
): Colis {
  const villeArrivee = villeDepuisAdresse(dto.destinataire_adresse);
  const villeDepart = 'Dakar';
  const distanceKm = distanceEntre(villeDepart, villeArrivee);
  const dateCreation = dto.created_at;
  const dateLivraisonPrevue = new Date(
    new Date(dateCreation).getTime() + 48 * 3600_000,
  ).toISOString();
  const statut = statutDepuisContrat(dto.statut);
  const expediteur = options.expediteur;
  const adresseExpediteur = expeditieurAdresse(expediteur, villeDepart);

  return {
    id: String(dto.id),
    numeroSuivi: numeroDepuisId(dto.id, dateCreation),
    clientId: String(dto.expediteur_id),
    expediteur: adresseExpediteur,
    destinataire: versAdresse(
      dto.destinataire_nom,
      dto.destinataire_adresse,
      villeArrivee,
    ),
    description: dto.description ?? '',
    poidsKg: Number(dto.poids_kg),
    statut,
    villeDepart,
    villeArrivee,
    distanceKm,
    dateCreation,
    dateLivraisonPrevue,
    dateLivraison: statut === 'livre' ? dateCreation : undefined,
    prixFcfa: 1500 + Math.round(Number(dto.poids_kg) * 450) + distanceKm * 12,
    historique:
      options.historique ??
      [
        {
          id: `${dto.id}-creation`,
          statut: 'en_attente',
          libelle: 'Colis enregistré',
          lieu: villeDepart,
          date: dateCreation,
          acteur: 'SenTransport',
        },
      ],
  };
}

function expeditieurAdresse(expediteur: Utilisateur | undefined, ville: string): Adresse {
  if (!expediteur) {
    return { nom: 'Expéditeur', telephone: '', adresse: '', ville };
  }
  return {
    nom: `${expediteur.prenom} ${expediteur.nom}`.trim(),
    telephone: expediteur.telephone,
    adresse: expediteur.ville,
    ville: expediteur.ville || ville,
  };
}

export function versLivraison(
  dto: LivraisonDTO,
  numeroSuivi: string,
  tournee = 'Tournée du jour',
): Livraison {
  return {
    id: String(dto.id),
    colisId: String(dto.colis_id),
    numeroSuivi,
    livreurId: String(dto.livreur_id),
    statut: statutDepuisContrat(dto.statut) as Livraison['statut'],
    dateAffectation: dto.created_at,
    dateLivraison: dto.statut === 'livre' ? dto.updated_at : undefined,
    motifEchec: dto.statut === 'echec' ? 'Destinataire absent' : undefined,
    tournee,
  };
}

export function versEvenement(dto: HistoriqueDTO): EvenementSuivi {
  const libelles: Record<StatutContrat, string> = {
    en_attente: 'Colis enregistré',
    en_transit: 'Colis en transit',
    livre: 'Colis livré',
    echec: 'Échec de livraison',
  };
  return {
    id: String(dto.id),
    statut: statutDepuisContrat(dto.statut),
    libelle: libelles[dto.statut] ?? 'Mise à jour',
    lieu: '',
    date: dto.date_changement,
    acteur: 'SenTransport',
  };
}

export function versColisDTO(colis: Colis): ColisDTO {
  return {
    id: Number(idDepuisNumero(colis.numeroSuivi)),
    expediteur_id: Number(colis.clientId.replace(/\D/g, '')) || 1,
    destinataire_nom: colis.destinataire.nom,
    destinataire_adresse: `${colis.destinataire.adresse}, ${colis.destinataire.ville}`,
    description: colis.description,
    poids_kg: colis.poidsKg,
    statut: statutVersContrat(colis.statut),
    created_at: colis.dateCreation,
  };
}

export function versUtilisateurDTO(utilisateur: Utilisateur): UtilisateurDTO {
  return {
    id: Number(utilisateur.id.replace(/\D/g, '')),
    nom: `${utilisateur.prenom} ${utilisateur.nom}`.trim(),
    email: utilisateur.email,
    role: roleVersContrat(utilisateur.role),
  };
}

export function versLivraisonDTO(livraison: Livraison, colisId: number): LivraisonDTO {
  return {
    id: Number(livraison.id.replace(/\D/g, '')) || Number(livraison.id) || 0,
    colis_id: colisId,
    livreur_id: Number(livraison.livreurId.replace(/\D/g, '')) || 1,
    statut: statutVersContrat(livraison.statut),
    created_at: livraison.dateAffectation,
    updated_at: livraison.dateLivraison ?? livraison.dateAffectation,
  };
}