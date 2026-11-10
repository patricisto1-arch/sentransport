import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../client';
import type { AffectationPayload, UpdateStatutPayload } from '../types';
import { clesColis } from './colis';
import {
  type AffectationDTO,
  type LivraisonDTO,
  numeroDepuisId,
  statutVersContrat,
  versLivraison,
} from '../contrat';

export const clesLivraisons = {
  tout: ['livraisons'] as const,
  liste: (livreurId?: string) => ['livraisons', 'liste', livreurId ?? 'toutes'] as const,
};

export function useLivraisons(livreurId?: string) {
  return useQuery({
    queryKey: clesLivraisons.liste(livreurId),
    queryFn: async () => {
      const { data } = await api.get<LivraisonDTO[]>('/livraisons/', {
        params: livreurId
          ? { livreur_id: Number(livreurId.replace(/\D/g, '')) }
          : undefined,
      });
      return data
        .filter(
          (dto) =>
            !livreurId ||
            String(dto.livreur_id) === livreurId.replace(/\D/g, ''),
        )
        .map((dto) =>
          versLivraison(dto, numeroDepuisId(dto.colis_id)),
        );
    },
    staleTime: 20_000,
  });
}

export function useMajStatutLivraison() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: string;
      payload: UpdateStatutPayload;
    }) => {
      const { data } = await api.patch<LivraisonDTO>(`/livraisons/${id}/statut`, {
        statut: statutVersContrat(payload.statut),
      });
      return versLivraison(data, numeroDepuisId(data.colis_id));
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: clesLivraisons.tout });
      void queryClient.invalidateQueries({ queryKey: clesColis.tout });
    },
  });
}

export function useAffecterColis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AffectationPayload) => {
      const corps: AffectationDTO = {
        colis_id: Number(payload.colisId.replace(/\D/g, '')),
        livreur_id: Number(payload.livreurId.replace(/\D/g, '')),
      };
      const { data } = await api.post<LivraisonDTO>('/livraisons/', corps);
      return versLivraison(data, numeroDepuisId(data.colis_id));
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: clesLivraisons.tout });
      void queryClient.invalidateQueries({ queryKey: clesColis.tout });
    },
  });
}
