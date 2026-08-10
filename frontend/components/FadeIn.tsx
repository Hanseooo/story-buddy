"use client";
import { motion, useReducedMotion } from "framer-motion";
import { ReactNode } from "react";

export function FadeInStagger({ children, className = "" }: { children: ReactNode; className?: string }) {
  const shouldReduceMotion = useReducedMotion();
  return (
    <motion.section
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0 },
        visible: { opacity: 1, transition: { staggerChildren: shouldReduceMotion ? 0 : 0.15, delayChildren: shouldReduceMotion ? 0 : 0.1 } }
      }}
      className={className}
    >
      {children}
    </motion.section>
  );
}

export function FadeIn({ children, className = "" }: { children: ReactNode; className?: string }) {
  const shouldReduceMotion = useReducedMotion();
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: shouldReduceMotion ? 0 : 30 },
        visible: { 
          opacity: 1, 
          y: 0, 
          transition: { type: "spring", stiffness: 200, damping: 25 } 
        }
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
