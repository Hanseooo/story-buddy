"use client";

import { motion } from "framer-motion";
import { Children, ReactNode } from "react";

export function StaggerGrid({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.ul
      className={className}
      initial="hidden"
      animate="show"
      variants={{
        hidden: { opacity: 0 },
        show: {
          opacity: 1,
          // The last item starts by 0.4s and lands about 0.25s later, however many items the grid holds (a gallery can hold 200).
          transition: { staggerChildren: Math.min(0.05, 0.4 / Math.max(1, Children.count(children))) },
        },
      }}
    >
      {children}
    </motion.ul>
  );
}

export function StaggerItem({ children }: { children: ReactNode }) {
  return (
    <motion.li
      variants={{
        hidden: { opacity: 0, y: 20, scale: 0.95 },
        show: { opacity: 1, y: 0, scale: 1 },
      }}
      whileHover={{ y: -2, transition: { type: "spring", bounce: 0, duration: 0.15 } }}
      transition={{ type: "spring", bounce: 0, duration: 0.25 }}
      className="block outline-none rounded-2xl"
    >
      {children}
    </motion.li>
  );
}
