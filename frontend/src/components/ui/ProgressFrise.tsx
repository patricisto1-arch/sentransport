import { motion, useReducedMotion } from 'framer-motion';
import type { StatutColis } from '@/api/types';
import { ETAPES_SUIVI, STATUTS } from '@/lib/constants';
import { useI18n } from '@/hooks/useI18n';
import { cn } from '@/lib/cn';

export function ProgressFrise({
  statut,
  compact = false,
}: {
  statut: StatutColis;
  compact?: boolean;
}) {
  const { t } = useI18n();
  const reduit = useReducedMotion();
  const meta = STATUTS[statut];
  const etape = meta.etape;
  const nombreEtapes = ETAPES_SUIVI.length;
  const marge = 50 / nombreEtapes;
  const largeurRemplie = (etape / (nombreEtapes - 1)) * (100 - 2 * marge);

  return (
    <div className="w-full">
      <div className="relative">
        <span
          aria-hidden
          style={{ left: `${marge}%`, right: `${marge}%` }}
          className="absolute top-[9px] h-[3px] rounded-full bg-line/[0.08] dark:bg-white/10"
        />
        <motion.span
          aria-hidden
          initial={{ width: 0 }}
          animate={{ width: `${largeurRemplie}%` }}
          transition={{
            duration: reduit ? 0 : 0.9,
            ease: [0.22, 1, 0.36, 1],
            delay: 0.15,
          }}
          style={{ left: `${marge}%` }}
          className={cn(
            'absolute top-[9px] h-[3px] rounded-full',
            statut === 'echec' ? 'bg-danger' : 'bg-accent',
          )}
        />
        <div className="relative flex items-start">
          {ETAPES_SUIVI.map((etapeSuivi, index) => {
            const atteinte = index <= etape;
            const courante = index === etape;
            const enEchec = statut === 'echec' && courante;
            return (
              <div
                key={etapeSuivi.statut}
                className="flex flex-1 flex-col items-center gap-2"
              >
                <span
                  aria-hidden
                  className={cn(
                    'relative z-10 grid place-items-center rounded-full border-2 transition-colors',
                    compact ? 'h-[19px] w-[19px]' : 'h-5 w-5',
                    atteinte
                      ? enEchec
                        ? 'border-danger bg-danger'
                        : 'border-accent bg-accent'
                      : 'border-line/15 bg-shell dark:border-white/20',
                  )}
                >
                  {atteinte ? (
                    <span className="h-1.5 w-1.5 rounded-full bg-white" />
                  ) : null}
                  {courante && !reduit && !enEchec ? (
                    <span className="absolute h-[19px] w-[19px] animate-ping rounded-full bg-accent/20" />
                  ) : null}
                </span>
                <span
                  className={cn(
                    'max-w-[76px] text-center text-[9.5px] leading-[1.25] tracking-[-0.01em]',
                    index <= etape ? 'font-semibold text-ink' : 'text-ink-mute',
                  )}
                >
                  {statut === 'echec' && index === nombreEtapes - 1
                    ? t('statut.echec')
                    : t(etapeSuivi.cle as 'etape.enregistre')}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      <span className="sr-only">
        Étape actuelle : {t(`statut.${statut}`)} ({etape + 1} sur {nombreEtapes})
      </span>
    </div>
  );
}
