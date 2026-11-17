import { describe, expect, it } from 'vitest';
import {
  ETAPES_SUIVI,
  FILTRES_STATUT,
  codeVille,
  distanceEntre,
  normaliserVille,
  villeParNom,
} from './constants';

describe('villes et distances', () => {
  it('ignore les accents, la casse et les tirets', () => {
    expect(normaliserVille('  Thiès ')).toBe('thies');
    expect(villeParNom('Thies')?.nom).toBe('Thiès');
    expect(villeParNom('saint louis')?.nom).toBe('Saint-Louis');
  });

  it('connaît Pikine et Guédiawaye, en banlieue de Dakar', () => {
    expect(codeVille('Pikine')).toBe('PIK');
    expect(villeParNom('Guediawaye')?.code).toBe('GDW');
    expect(distanceEntre('Dakar', 'Pikine')).toBe(15);
  });

  it('calcule la même distance avec ou sans accent', () => {
    expect(distanceEntre('Dakar', 'Thiès')).toBe(70);
    expect(distanceEntre('Dakar', 'Thies')).toBe(70);
  });

  it('renvoie 0 plutôt qu’une distance inventée pour une ville inconnue', () => {
    expect(distanceEntre('Dakar', 'Zzzville')).toBe(0);
  });
});

describe('étapes de suivi', () => {
  it('ne propose que les statuts connus de l’API', () => {
    expect(ETAPES_SUIVI.map((e) => e.statut)).toEqual(['en_attente', 'en_transit', 'livre']);
    expect(FILTRES_STATUT).not.toContain('pris_en_charge');
  });
});
