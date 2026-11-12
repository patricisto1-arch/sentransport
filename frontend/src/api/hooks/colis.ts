import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type {
  Colis,
  ColisListParams,
  CreateColisPayload,
  Paginated,
  UpdateColisPayload,
} from '../types';
import {
  type ColisDTO,
  type CreationColisDTO,
  type MajColisDTO,
  idDepuisNumero,
  versColis,
} from '../contrat';
import { useAuthStore } from '@/store/auth';

export const clesColis = {
  tout: ['colis'] as const,
  liste: (params: ColisListParams) => ['colis', 'liste', params] as const,
  detail: (id: string) => ['colis', 'detail', id] as const,
  suivi: (numero: string) => ['colis', 'suivi', numero] as const,
};

export function useColisList(params: ColisListParams = {}) {
  const utilisateur = useAuthStore((s) => s.utilisateur);
  return useQuery({
    queryKey: [...clesColis.liste(params), utilisateur?.id],
    queryFn: async () => {
      const { data } = await api.get<ColisDTO[]>('/colis/');
      const tous = data.map((dto) =>
        versColis(dto, {
          expediteur:
            utilisateur && String(dto.expediteur_id) === utilisateur.id
              ? utilisateur
              : undefined,
        }),
      );
      const recherche = params.q?.trim().toLowerCase();
      const filtres = tous.filter((colis) => {
        if (params.statut && params.statut !== 'tous' && colis.statut !== params.statut) {
          return false;
        }
        if (params.ville && colis.villeArrivee !== params.ville) return false;
        if (params.livreurId && colis.livreurId !== params.livreurId) return false;
        if (!recherche) return true;
        return [
          colis.numeroSuivi,
          colis.destinataire.nom,
          colis.destinataire.adresse,
          colis.description,
          colis.villeArrivee,
        ]
          .join(' ')
          .toLowerCase()
          .includes(recherche);
      });
      const tries = [...filtres].sort((a, b) => {
        switch (params.tri) {
          case 'ancien':
            return +new Date(a.dateCreation) - +new Date(b.dateCreation);
          case 'poids':
            return b.poidsKg - a.poidsKg;
          case 'numero':
            return a.numeroSuivi.localeCompare(b.numeroSuivi);
          default:
            return +new Date(b.dateCreation) - +new Date(a.dateCreation);
        }
      });
      const page = Math.max(1, params.page ?? 1);
      const limit = Math.max(1, params.limit ?? 8);
      const debut = (page - 1) * limit;
      return {
        items: tries.slice(debut, debut + limit),
        total: tries.length,
        page,
        limit,
        pageCount: Math.max(1, Math.ceil(tries.length / limit)),
      } satisfies Paginated<Colis>;
    },
    placeholderData: (precedent) => precedent,
    staleTime: 30_000,
  });
}

export function useColis(id?: string) {
  const utilisateur = useAuthStore((s) => s.utilisateur);
  return useQuery({
    queryKey: clesColis.detail(id ?? ''),
    queryFn: async () => {
      const { data } = await api.get<ColisDTO>(`/colis/${idDepuisNumero(id ?? '')}`);
      return versColis(data, {
        expediteur:
          utilisateur && String(data.expediteur_id) === utilisateur.id
            ? utilisateur
            : undefined,
      });
    },
    enabled: Boolean(id),
  });
}

export function useCreerColis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateColisPayload) => {
      const corps: CreationColisDTO = {
        destinataire_nom: payload.destinataire.nom,
        destinataire_adresse: `${payload.destinataire.adresse}, ${payload.destinataire.ville}`,
        description: payload.description,
        poids_kg: payload.poidsKg,
      };
      const { data } = await api.post<ColisDTO>('/colis/', corps);
      return versColis(data);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: clesColis.tout });
    },
  });
}

export function useModifierColis(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateColisPayload) => {
      const corps: MajColisDTO = {};
      if (payload.description !== undefined) corps.description = payload.description;
      if (payload.poidsKg !== undefined) corps.poids_kg = payload.poidsKg;
      if (payload.destinataire) {
        corps.destinataire_nom = payload.destinataire.nom;
        corps.destinataire_adresse = `${payload.destinataire.adresse}, ${payload.destinataire.ville}`;
      }
      const { data } = await api.put<ColisDTO>(
        `/colis/${idDepuisNumero(id)}`,
        corps,
      );
      return versColis(data);
    },
    onSuccess: (colis) => {
      queryClient.setQueryData(clesColis.detail(id), colis);
      void queryClient.invalidateQueries({ queryKey: clesColis.tout });
    },
  });
}

export function useSupprimerColis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/colis/${idDepuisNumero(id)}`);
      return id;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: clesColis.tout });
    },
  });
}
