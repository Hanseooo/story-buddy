"use client";

import { useSyncExternalStore, useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { WifiSlash, WifiHigh } from "@phosphor-icons/react";

function subscribeOnlineStatus(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

function getSnapshot() {
  return !navigator.onLine;
}

function getServerSnapshot() {
  return false;
}

export default function OfflineIndicator() {
  const isOffline = useSyncExternalStore(
    subscribeOnlineStatus,
    getSnapshot,
    getServerSnapshot
  );
  const [showReconnected, setShowReconnected] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setShowReconnected(true);
      const timer = setTimeout(() => {
        setShowReconnected(false);
      }, 3000);
      return () => clearTimeout(timer);
    };

    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("online", handleOnline);
    };
  }, []);

  return (
    <AnimatePresence>
      {isOffline && (
        <motion.div
          key="offline-banner"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          data-testid="offline-indicator-banner"
          role="status"
          aria-live="polite"
          className="fixed top-4 left-1/2 -translate-x-1/2 z-[var(--z-toast,100)] w-[calc(100%-2rem)] max-w-md pointer-events-none"
        >
          <div className="bg-secondary text-on-secondary border border-secondary/40 rounded-full px-4 py-2.5 shadow-md flex items-center justify-center gap-2.5 text-xs sm:text-sm font-kid font-bold text-center">
            <WifiSlash className="size-4 shrink-0 text-foreground" weight="bold" />
            <span>You&apos;re offline right now. Your work will sync once you reconnect.</span>
          </div>
        </motion.div>
      )}

      {!isOffline && showReconnected && (
        <motion.div
          key="reconnected-banner"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          role="status"
          aria-live="polite"
          className="fixed top-4 left-1/2 -translate-x-1/2 z-[var(--z-toast,100)] w-[calc(100%-2rem)] max-w-md pointer-events-none"
        >
          <div className="bg-success text-on-success border border-success/40 rounded-full px-4 py-2.5 shadow-md flex items-center justify-center gap-2.5 text-xs sm:text-sm font-kid font-bold text-center">
            <WifiHigh className="size-4 shrink-0" weight="bold" />
            <span>Back online. Your story is connected again.</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
