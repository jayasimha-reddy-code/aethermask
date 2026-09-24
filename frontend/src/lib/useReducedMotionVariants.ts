/**
 * AetherMask (CipherShift) :: reduced-motion aware variant factory
 *
 * WHY THIS EXISTS
 * ---------------
 * `<MotionConfig reducedMotion="user">` disables transform/layout animations
 * outright when the OS asks for reduced motion. That satisfies WCAG 2.3.3, but
 * Apple's own guidance (and the accessibility literature) is that instant
 * snapping can feel *broken* because the user loses spatial context. The
 * recommended pattern is to REPLACE sweeping movement with a short cross-fade
 * rather than removing the feedback entirely.
 *
 * These factories return variants whose translation collapses to zero while a
 * brief opacity fade is preserved, giving graceful degradation instead of a
 * hard cut.
 */

import { useMemo } from 'react';
import { useReducedMotion, type Transition, type Variants } from 'motion/react';
import { easeEmphasized, easeQuick } from './motion';

/** Directional stage slide that degrades to a pure cross-fade. */
export function useStageVariants(): Variants {
  const reduce = useReducedMotion();

  return useMemo<Variants>(() => {
    const distance = reduce ? 0 : 28;
    const exitDistance = reduce ? 0 : 20;
    return {
      enter: (direction: number) => ({
        opacity: 0,
        x: direction >= 0 ? distance : -distance,
      }),
      center: {
        opacity: 1,
        x: 0,
        transition: { ...easeEmphasized, when: 'beforeChildren' },
      },
      exit: (direction: number) => ({
        opacity: 0,
        x: direction >= 0 ? -exitDistance : exitDistance,
        transition: easeQuick,
      }),
    };
  }, [reduce]);
}

/** Vertical reveal that degrades to a pure cross-fade. */
export function useRevealVariants(offset = 8): Variants {
  const reduce = useReducedMotion();

  return useMemo<Variants>(
    () => ({
      hidden: { opacity: 0, y: reduce ? 0 : -offset },
      visible: { opacity: 1, y: 0, transition: easeEmphasized },
      exit: { opacity: 0, y: reduce ? 0 : -offset * 0.75, transition: easeQuick },
    }),
    [reduce, offset],
  );
}

/**
 * Staggered list. Under reduced motion the per-item offset collapses and the
 * stagger interval shortens so long lists still resolve promptly.
 */
export function useListVariants(): {
  container: Variants;
  item: Variants;
} {
  const reduce = useReducedMotion();

  return useMemo(() => {
    const stagger = reduce ? 0.012 : 0.035;
    return {
      container: {
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: { staggerChildren: stagger, delayChildren: reduce ? 0 : 0.04 },
        },
      },
      item: {
        hidden: { opacity: 0, y: reduce ? 0 : 6 },
        visible: { opacity: 1, y: 0, transition: easeEmphasized },
      },
    };
  }, [reduce]);
}

/** Verdict settle. The spring is swapped for a gentle fade under reduced motion. */
export function useVerdictVariants(): Variants {
  const reduce = useReducedMotion();

  return useMemo<Variants>(() => {
    const transition: Transition = reduce
      ? { type: 'tween', duration: 0.22, ease: [0.4, 0, 0.2, 1] }
      : { type: 'spring', stiffness: 320, damping: 28, mass: 0.8 };
    return {
      hidden: { opacity: 0, scale: reduce ? 1 : 0.97, y: reduce ? 0 : 6 },
      visible: { opacity: 1, scale: 1, y: 0, transition },
    };
  }, [reduce]);
}

/**
 * Whether decorative, indefinite motion (ambient sheens, pulse rings) should
 * run at all. These loop without user interaction and are exactly the category
 * the accessibility guidance says to drop entirely rather than soften.
 */
export function useAmbientMotionAllowed(): boolean {
  return !useReducedMotion();
}
