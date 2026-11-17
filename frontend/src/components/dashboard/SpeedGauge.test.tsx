import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { SpeedGauge } from './SpeedGauge';
import { rendre } from '@/tests/render';

describe('SpeedGauge', () => {
  it('n’affiche pas 100 % tant qu’aucun colis n’est livré', () => {
    rendre(<SpeedGauge pourcentage={null} aLheure={0} enRetard={0} />);

    expect(screen.getAllByText('Aucune livraison terminée').length).toBeGreaterThan(0);
    expect(screen.queryByText('%')).not.toBeInTheDocument();
  });

  it('affiche le pourcentage réel quand des colis sont livrés', () => {
    rendre(<SpeedGauge pourcentage={50} aLheure={1} enRetard={1} />);

    expect(screen.getByText('%')).toBeInTheDocument();
    expect(screen.getByText('2 colis livrés à temps')).toBeInTheDocument();
  });
});
