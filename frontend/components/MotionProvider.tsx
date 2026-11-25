"use client";

import { MotionConfig } from "framer-motion";

// The reduced-motion block in globals.css only reaches CSS animations.
// framer-motion runs from JS, so it needs its own switch to honour the OS setting.
export default function MotionProvider({ children }: { children: React.ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
