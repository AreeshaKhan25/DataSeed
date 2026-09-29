import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

/**
 * The opening animation.
 *
 * Three rules, because a splash screen that gets any of them wrong is worse
 * than no splash at all:
 *
 *  1. It never blocks the app. The overlay sits on top while everything boots
 *     underneath, so the time is spent, not wasted.
 *  2. It never waits on its own asset. If the GIF has not arrived within
 *     `GRACE_MS` the splash is abandoned outright — a slow connection must not
 *     be punished with a longer wait for a decoration.
 *  3. It shows once per visit, not on every re-render or route change.
 */

const ASSET = "/dataseed-intro.gif";
const STORAGE_KEY = "dataseed:intro-seen";
/** Roughly the GIF's own length, so it is not cut off mid-reveal. */
const PLAY_MS = 2600;
/** How long to wait for the asset before giving up on the splash entirely. */
const GRACE_MS = 900;

function alreadySeen(): boolean {
  try {
    // sessionStorage, not localStorage: once per visit rather than once ever.
    // A returning visitor in a new tab should still get the opening, and on
    // demo day nobody wants it silently suppressed because the machine has
    // opened the site before. Swap to localStorage for once-per-browser.
    return sessionStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    // Private mode or blocked storage: treat as unseen and simply show it.
    return false;
  }
}

function markSeen(): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, "1");
  } catch {
    /* nothing to do — the splash just plays again next time */
  }
}

export function Intro() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (alreadySeen()) return;

    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      markSeen();
      return;
    }

    let cancelled = false;
    let hideTimer: number | undefined;

    // Decode the GIF before showing anything, so the first thing on screen is
    // the animation rather than an empty white panel.
    const image = new Image();
    const grace = window.setTimeout(() => {
      if (!cancelled && !image.complete) {
        cancelled = true;
        markSeen();
      }
    }, GRACE_MS);

    image.onload = () => {
      window.clearTimeout(grace);
      if (cancelled) return;
      setVisible(true);
      markSeen();
      hideTimer = window.setTimeout(() => setVisible(false), PLAY_MS);
    };
    image.onerror = () => {
      window.clearTimeout(grace);
      cancelled = true;
      markSeen();
    };
    image.src = ASSET;

    return () => {
      cancelled = true;
      window.clearTimeout(grace);
      if (hideTimer) window.clearTimeout(hideTimer);
    };
  }, []);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="intro"
          className="fixed inset-0 z-[100] flex items-center justify-center"
          // Matched to the GIF's own background (#fdfdfd) so its edges are
          // invisible; against the page canvas it read as a floating box.
          style={{ background: "#fdfdfd" }}
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
          aria-hidden
          // Clicking through is the polite escape hatch for anyone who has
          // seen it and just wants the app.
          onClick={() => setVisible(false)}
        >
          <motion.img
            src={ASSET}
            alt=""
            className="w-[380px] max-w-[80vw] select-none"
            draggable={false}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
