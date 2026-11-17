import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { ProgressFrise } from './ProgressFrise';
import { rendre } from '@/tests/render';

describe('ProgressFrise', () => {
  it('affiche les trois étapes réelles', () => {
    rendre(<ProgressFrise statut="en_transit" />);

    expect(screen.getByText('Enregistré')).toBeInTheDocument();
    expect(screen.getByText('En transit')).toBeInTheDocument();
    expect(screen.getByText('Livré')).toBeInTheDocument();
    expect(screen.queryByText('Pris en charge')).not.toBeInTheDocument();
  });

  it('remplace « Livré » par « Échec » quand la livraison échoue', () => {
    rendre(<ProgressFrise statut="echec" />);

    expect(screen.getByText('Échec')).toBeInTheDocument();
    expect(screen.queryByText('Livré')).not.toBeInTheDocument();
  });
});
