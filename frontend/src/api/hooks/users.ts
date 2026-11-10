import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../client';
import type { AuthResponse, LoginPayload, RegisterPayload, Role, Utilisateur } from '../types';
import {
  type ConnexionDTO,
  type InscriptionDTO,
  type JetonDTO,
  type UtilisateurDTO,
  versUtilisateur,
} from '../contrat';

export const clesUsers = {
  tout: ['users'] as const,
  liste: (role?: Role) => ['users', 'liste', role ?? 'tous'] as const,
  moi: ['users', 'moi'] as const,
};

export function useConnexion() {
  return useMutation({
    mutationFn: async (payload: LoginPayload) => {
      const { data: jeton } = await api.post<JetonDTO>('/utilisateurs/auth/login', {
        email: payload.email,
        mot_de_passe: payload.password,
      } satisfies ConnexionDTO);
      const { data: profil } = await api.get<UtilisateurDTO>('/utilisateurs/me', {
        headers: { Authorization: `Bearer ${jeton.access_token}` },
      });
      return {
        token: jeton.access_token,
        utilisateur: versUtilisateur(profil),
      } satisfies AuthResponse;
    },
  });
}

export function useInscription() {
  return useMutation({
    mutationFn: async (payload: RegisterPayload) => {
      await api.post<UtilisateurDTO>('/utilisateurs/auth/register', {
        nom: `${payload.prenom} ${payload.nom}`.trim(),
        email: payload.email,
        mot_de_passe: payload.password,
        role: payload.role,
      } satisfies InscriptionDTO);
      const { data: jeton } = await api.post<JetonDTO>('/utilisateurs/auth/login', {
        email: payload.email,
        mot_de_passe: payload.password,
      } satisfies ConnexionDTO);
      const { data: profil } = await api.get<UtilisateurDTO>('/utilisateurs/me', {
        headers: { Authorization: `Bearer ${jeton.access_token}` },
      });
      return {
        token: jeton.access_token,
        utilisateur: versUtilisateur(profil),
      } satisfies AuthResponse;
    },
  });
}

export function useMoi(actif = true) {
  return useQuery({
    queryKey: clesUsers.moi,
    queryFn: async () => {
      const { data } = await api.get<UtilisateurDTO>('/utilisateurs/me');
      return versUtilisateur(data);
    },
    enabled: actif,
    staleTime: 60_000,
  });
}

export function useUtilisateurs(role?: Role) {
  return useQuery({
    queryKey: clesUsers.liste(role),
    queryFn: async () => {
      // Le contrat n'expose que la liste des livreurs (admin).
      if (role !== 'livreur') return [] as Utilisateur[];
      const { data } = await api.get<UtilisateurDTO[]>('/utilisateurs/livreurs');
      return data.map(versUtilisateur);
    },
    enabled: role === 'livreur',
  });
}
