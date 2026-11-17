import { describe, expect, it } from 'vitest';
import { adresseComplete } from './format';

describe('adresseComplete', () => {
  it('ne répète pas la ville déjà présente à la fin de l’adresse', () => {
    expect(adresseComplete('Rue 10, Pikine', 'Pikine')).toBe('Rue 10, Pikine');
    expect(adresseComplete('Rue 5, Thies', 'Thiès')).toBe('Rue 5, Thies');
  });

  it('ajoute la ville quand elle est absente', () => {
    expect(adresseComplete('Rue 10', 'Pikine')).toBe('Rue 10, Pikine');
  });
});
