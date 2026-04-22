"use client";
import { useEffect, useRef, useState } from "react";

const GLYPHS = "!<>-_\\/[]{}—=+*^?#________אבגדהוזחטיכלמנסעפצקרשת";

/**
 * Text-scramble effect: letters decode from random glyphs into the target text.
 * Triggers once when in view. Subtle, cinematic.
 */
export default function TextScramble({
  text,
  duration = 1200,
  delay = 0,
  className = "",
}: { text: string; duration?: number; delay?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [display, setDisplay] = useState(text);
  const [triggered, setTriggered] = useState(false);

  useEffect(() => {
    if (!ref.current || triggered) return;
    const io = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      io.disconnect();
      setTriggered(true);
      setTimeout(() => runScramble(), delay);
    }, { threshold: 0.4 });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [text, delay, triggered]);

  function runScramble() {
    const target = text;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      // How many characters are "locked" on their final value
      const locked = Math.floor(target.length * p);
      let out = "";
      for (let i = 0; i < target.length; i++) {
        if (i < locked || /\s/.test(target[i])) {
          out += target[i];
        } else {
          out += GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
        }
      }
      setDisplay(out);
      if (p < 1) requestAnimationFrame(tick);
      else setDisplay(target);
    };
    setDisplay(target.split("").map(() => GLYPHS[Math.floor(Math.random() * GLYPHS.length)]).join(""));
    requestAnimationFrame(tick);
  }

  return <span ref={ref} className={className}>{triggered ? display : text}</span>;
}
