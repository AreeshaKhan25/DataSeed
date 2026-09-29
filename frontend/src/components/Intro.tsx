import { AnimatePresence, motion } from "framer-motion";
import { useEffect } from "react";
import { useStore } from "../lib/store";

const ASSET = "/dataseed-intro.gif";
/** GIF duration in ms before transitioning to the app */
const PLAY_MS = 2600;

export function Intro() {
  const { introActive, finishIntro } = useStore();

  useEffect(() => {
    if (!introActive) return;

    const timer = window.setTimeout(() => {
      finishIntro();
    }, PLAY_MS);

    return () => {
      window.clearTimeout(timer);
    };
  }, [introActive, finishIntro]);

  return (
    <AnimatePresence>
      {introActive && (
        <motion.div
          key="intro-loader"
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center cursor-pointer select-none"
          style={{ background: "#fdfdfd" }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          aria-label="Click to skip intro loader"
          onClick={finishIntro}
        >
          <motion.img
            src={ASSET}
            alt="DataSeed Engine Loading..."
            // The new clip has a textured studio background rather than a flat
            // one, so it cannot be blended edge to edge. Rounding it and
            // lifting it off the page makes the boundary deliberate instead.
            className="w-[480px] max-w-[86vw] rounded-2xl shadow-lift select-none"
            draggable={false}
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          />
          <div className="mt-4 text-[12.5px] font-semibold text-secondary tracking-wide flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-primary animate-pulse" />
            Initializing Synthetic Engine...
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
