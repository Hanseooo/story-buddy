"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CaretDown, Check, House, User } from "@phosphor-icons/react";

type Classroom = { id: string; name: string };

export default function ClassroomSwitcher({
  classrooms,
}: {
  classrooms: Classroom[];
}) {
  const pathname = usePathname();
  const router = useRouter();
  const currentId = pathname.match(/^\/classroom\/([^/]+)/)?.[1];
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (classrooms.length === 0) return null;

  const currentClassroom = classrooms.find((c) => c.id === currentId);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-sm font-bold bg-muted border-2 border-primary/10 rounded-xl px-3 py-1.5 hover:bg-primary/5 hover:border-primary/20 transition-all focus:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-2 focus-visible:ring-offset-surface outline-none"
        aria-label="Switch classroom"
        aria-expanded={isOpen}
      >
        <span className="truncate max-w-[120px] sm:max-w-[200px]">
          {currentClassroom ? currentClassroom.name : "Select classroom"}
        </span>
        <CaretDown weight="bold" className={`transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 25 }}
            className="absolute top-full left-0 mt-2 w-56 sm:w-64 bg-surface border-2 border-primary/15 rounded-2xl shadow-[0_12px_40px_rgba(49,85,217,0.12)] overflow-hidden z-50 origin-top-left"
          >
            <div className="max-h-64 overflow-y-auto overscroll-contain py-2">
              {classrooms.map((c) => {
                const isActive = c.id === currentId;
                return (
                  <button
                    key={c.id}
                    onClick={() => {
                      setIsOpen(false);
                      router.push(`/classroom/${c.id}`);
                    }}
                    className={`w-full text-left px-4 py-2.5 flex items-center justify-between transition-colors outline-none focus-visible:bg-primary/10 ${
                      isActive ? "bg-primary/5 text-primary" : "text-foreground hover:bg-muted"
                    }`}
                  >
                    <span className="font-bold truncate pr-4">{c.name}</span>
                    {isActive && <Check weight="bold" className="shrink-0 text-primary" />}
                  </button>
                );
              })}
            </div>
            <div className="border-t border-primary/10 p-2">
              <button
                onClick={() => {
                  setIsOpen(false);
                  router.push("/classroom");
                }}
                className="w-full text-left px-3 py-2.5 flex items-center gap-2 text-sm font-bold text-foreground/80 hover:text-primary hover:bg-primary/5 rounded-xl transition-colors outline-none focus-visible:ring-2 focus-visible:ring-secondary"
              >
                <House weight="fill" className="text-primary/70 shrink-0" />
                Teacher&apos;s Desk
              </button>
              <button
                onClick={() => {
                  setIsOpen(false);
                  router.push("/settings");
                }}
                className="sm:hidden w-full text-left px-3 py-2.5 flex items-center gap-2 text-sm font-bold text-foreground/80 hover:text-primary hover:bg-primary/5 rounded-xl transition-colors outline-none focus-visible:ring-2 focus-visible:ring-secondary mt-1"
              >
                <User weight="fill" className="text-primary/70 shrink-0" />
                Settings
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
