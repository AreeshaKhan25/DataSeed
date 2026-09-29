import type { Transition, Variants } from "framer-motion";

// One motion vocabulary for the whole app. Screens import from here rather than
// inventing their own durations, so everything moves with the same rhythm.

export const spring: Transition = { type: "spring", stiffness: 380, damping: 30, mass: 0.7 };
export const softSpring: Transition = { type: "spring", stiffness: 210, damping: 26 };
export const ease: Transition = { duration: 0.28, ease: [0.16, 1, 0.3, 1] };
export const quick: Transition = { duration: 0.16, ease: [0.16, 1, 0.3, 1] };

/** Page-level enter/exit. Forward motion is upward, so back feels like return. */
export const page: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { ...ease, staggerChildren: 0.045, delayChildren: 0.04 } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.16 } },
};

/** A child of `page`. Rises into place as its parent staggers. */
export const rise: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: ease },
  exit: { opacity: 0, transition: quick },
};

/** List rows. Cheaper than `rise` because there are many of them. */
export const row: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: Math.min(i * 0.022, 0.4), duration: 0.24, ease: [0.16, 1, 0.3, 1] },
  }),
};

export const popIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  show: { opacity: 1, scale: 1, transition: spring },
  exit: { opacity: 0, scale: 0.98, transition: quick },
};

/** Press feedback shared by every interactive surface. */
export const pressable = {
  whileHover: { y: -1 },
  whileTap: { scale: 0.975 },
  transition: spring,
};

export const cardHover = {
  whileHover: { y: -3, boxShadow: "0 4px 12px rgba(22,32,46,.07), 0 12px 32px rgba(22,32,46,.06)" },
  transition: softSpring,
};
