"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";

export default function WorkflowShowcase({ isMobileForm = false }: { isMobileForm?: boolean }) {
  const [phase, setPhase] = useState(0); // 0: Input, 1: Preset, 2: Loading, 3: Result
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    const timer = setInterval(() => {
      setPhase((prev) => (prev + 1) % 4);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className={`w-full relative flex items-center justify-center overflow-hidden ${isMobileForm ? 'h-full p-4 bg-background' : 'bg-surface/50 neo-border rounded-[32px] p-6 sm:p-12 min-h-[450px]'}`}>
      <AnimatePresence mode="wait">
        
        {/* Phase 0: Text Input */}
        {phase === 0 && (
          <motion.div 
            key="phase0"
            initial={{ opacity: 0, scale: shouldReduceMotion ? 1 : 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: shouldReduceMotion ? 1 : 1.05 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col w-full max-w-md h-full justify-center"
          >
            <div className="h-40 w-full p-2 bg-transparent flex flex-col justify-start">
              <span className="font-extrabold text-foreground text-3xl leading-tight">
                Maya found a tiny door beneath the old mango tree...
              </span>
              <div className="w-1.5 h-8 bg-primary animate-pulse mt-1" />
            </div>
            
            <div className="mt-6 flex flex-col gap-3 bg-surface p-3 rounded-[20px] border border-primary/10 shadow-[0_12px_30px_rgba(49,85,217,0.12)] shrink-0">
               <div className="flex items-center gap-3 bg-background px-3 py-2.5 rounded-xl border border-primary/10">
                 <div className="relative w-8 h-8 flex items-center justify-center">
                    <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 36 36">
                      <circle cx="18" cy="18" r="16" fill="none" className="stroke-muted" strokeWidth="4" />
                      <circle cx="18" cy="18" r="16" fill="none" className="stroke-secondary" strokeWidth="4" strokeDasharray="100" strokeDashoffset="0" strokeLinecap="round" />
                    </svg>
                    <span className="text-[11px] font-bold text-primary">10</span>
                 </div>
                 <div className="flex flex-col">
                   <span className="text-[11px] font-extrabold text-foreground leading-none mb-1">Ready!</span>
                   <span className="text-[9px] font-bold text-foreground/60 leading-none">5 words min</span>
                 </div>
               </div>
               <div className="h-12 w-full bg-primary rounded-xl flex items-center justify-center text-on-primary font-extrabold text-sm shadow-[0_3px_0_var(--color-primary-deep)]">
                 Make my book
               </div>
            </div>
          </motion.div>
        )}

        {/* Phase 1: Select Preset */}
        {phase === 1 && (
          <motion.div 
            key="phase1"
            initial={{ opacity: 0, scale: shouldReduceMotion ? 1 : 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: shouldReduceMotion ? 1 : 1.05 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col w-full max-w-md items-center h-full justify-center"
          >
            <div className="font-kid font-extrabold text-foreground/60 text-sm mb-3 self-start ml-1">Pick a look</div>
            <div className="flex gap-2 w-full">
              {/* Cel / Cartoon */}
              <div className="flex-1 rounded-2xl bg-surface border border-primary/20 flex flex-col items-center justify-center py-4 gap-1.5 shadow-sm">
                <span className="text-3xl">📺</span>
                <span className="font-kid text-[11px] font-extrabold text-foreground">Cartoon</span>
              </div>
              
              {/* Comic */}
              <motion.div 
                className="flex-1 rounded-2xl bg-surface border border-primary ring-1 ring-primary flex flex-col items-center justify-center py-4 gap-1.5 shadow-sm relative"
                initial={{ scale: 1 }}
                animate={shouldReduceMotion ? { scale: 1 } : { scale: [1, 1.05, 1] }}
                transition={{ duration: 0.6 }}
              >
                <div className="absolute -top-1.5 -right-1.5 bg-secondary text-primary rounded-full p-0.5 border-2 border-surface">
                   <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                </div>
                <span className="text-3xl">💥</span>
                <span className="font-kid text-[11px] font-extrabold text-foreground">Comic</span>
              </motion.div>
              
              {/* Gouache / Painted */}
              <div className="flex-1 rounded-2xl bg-surface border border-primary/20 flex flex-col items-center justify-center py-4 gap-1.5 shadow-sm">
                <span className="text-3xl">🎨</span>
                <span className="font-kid text-[11px] font-extrabold text-foreground">Painted</span>
              </div>
            </div>
          </motion.div>
        )}

        {/* Phase 2: Loading Graph */}
        {phase === 2 && (
          <motion.div 
            key="phase2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col items-center gap-6"
          >
            <div className="flex gap-3">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-4 h-4 rounded-full bg-secondary shadow-[0_4px_8px_rgba(242,200,95,0.4)]"
                  animate={shouldReduceMotion ? { opacity: [0.4, 1, 0.4] } : { y: [0, -12, 0] }}
                  transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                />
              ))}
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="font-kid text-primary font-extrabold text-xl">
                Making magic...
              </div>
              <div className="font-kid text-foreground/60 text-sm text-center px-4">
                Painting the pictures and setting up the pages.
              </div>
            </div>
          </motion.div>
        )}

        {/* Phase 3: Result */}
        {phase === 3 && (
          <motion.div 
            key="phase3"
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: shouldReduceMotion ? 0 : -30 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
            className="w-full max-w-lg rounded-3xl bg-surface border border-primary/10 shadow-[0_12px_40px_rgba(24,32,74,0.1)] overflow-hidden flex flex-col"
          >
            <div className="h-44 w-full bg-[#E9EDFC] relative overflow-hidden flex items-center justify-center">
               {!shouldReduceMotion && (
                 <motion.div 
                   className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/50 to-transparent"
                   animate={{ translateX: ["-100%", "100%"] }}
                   transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
                 />
               )}
               <span className="text-6xl drop-shadow-md">🌳</span>
            </div>
            <div className="p-5 flex flex-col gap-3">
              <p className="font-kid text-[13px] leading-relaxed text-foreground/80 text-center px-2">
                Behind the leaves, she saw a handle made of twisted vines, glowing softly in the shade.
              </p>
              <div className="mt-2 h-10 w-full bg-primary/10 rounded-xl flex items-center justify-center text-primary font-bold text-sm hover:bg-primary/20 transition-colors cursor-pointer">
                Next Page
              </div>
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  );
}
