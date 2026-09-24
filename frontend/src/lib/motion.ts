/**
 * AetherMask (CipherShift) :: motion design system
 *
 * All motion is meaning-bearing and restrained:
 *   - One easing curve: cubic-bezier(0.22, 1, 0.36, 1)
 *   - Durations between 140ms and 260ms
 *   - No bouncy springs or looping animations
 *   - Transitions color, opacity, and transform only
 */

import type { Transition, Variants } from 'motion/react';

/* -------------------------------------------------------------------------- */
/*  Shared transitions                                                         */
/* -------------------------------------------------------------------------- */

export const easeEmphasized: Transition = {
  type: 'tween',
  ease: [0.22, 1, 0.36, 1],
  duration: 0.24,
};

export const easeQuick: Transition = {
  type: 'tween',
  ease: [0.22, 1, 0.36, 1],
  duration: 0.16,
};

export const springSettle: Transition = {
  type: 'tween',
  ease: [0.22, 1, 0.36, 1],
  duration: 0.22,
};

export const springSoft: Transition = {
  type: 'tween',
  ease: [0.22, 1, 0.36, 1],
  duration: 0.2,
};

/* -------------------------------------------------------------------------- */
/*  Stage transitions (directional)                                            */
/* -------------------------------------------------------------------------- */

export const stageVariants: Variants = {
  enter: (direction: number) => ({
    opacity: 0,
    x: direction >= 0 ? 16 : -16,
  }),
  center: {
    opacity: 1,
    x: 0,
    transition: { ...easeEmphasized, when: 'beforeChildren' },
  },
  exit: (direction: number) => ({
    opacity: 0,
    x: direction >= 0 ? -12 : 12,
    transition: easeQuick,
  }),
};

/* -------------------------------------------------------------------------- */
/*  Content reveal                                                             */
/* -------------------------------------------------------------------------- */

export const revealVariants: Variants = {
  hidden: { opacity: 0, y: -4 },
  visible: { opacity: 1, y: 0, transition: easeEmphasized },
  exit: { opacity: 0, y: -4, transition: easeQuick },
};

export const fadeVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: easeEmphasized },
  exit: { opacity: 0, transition: easeQuick },
};

/* -------------------------------------------------------------------------- */
/*  Staggered lists                                                            */
/* -------------------------------------------------------------------------- */

export const listVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.03, delayChildren: 0.02 },
  },
};

export const listItemVariants: Variants = {
  hidden: { opacity: 0, y: 4 },
  visible: { opacity: 1, y: 0, transition: easeEmphasized },
};

/* -------------------------------------------------------------------------- */
/*  Verdict / result emphasis                                                  */
/* -------------------------------------------------------------------------- */

export const verdictVariants: Variants = {
  hidden: { opacity: 0, y: 4 },
  visible: { opacity: 1, y: 0, transition: easeEmphasized },
};

/* -------------------------------------------------------------------------- */
/*  Overlays                                                                   */
/* -------------------------------------------------------------------------- */

export const backdropVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: easeQuick },
  exit: { opacity: 0, transition: easeQuick },
};

export const panelVariants: Variants = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0, transition: easeEmphasized },
  exit: { opacity: 0, y: 4, transition: easeQuick },
};

export const drawerVariants: Variants = {
  hidden: { opacity: 0, x: 20 },
  visible: { opacity: 1, x: 0, transition: easeEmphasized },
  exit: { opacity: 0, x: 16, transition: easeQuick },
};

/* -------------------------------------------------------------------------- */
/*  Interaction feedback                                                       */
/* -------------------------------------------------------------------------- */

export const pressable = {
  whileTap: { scale: 0.98 },
  transition: easeQuick,
} as const;

export const liftable = {
  transition: easeQuick,
} as const;
