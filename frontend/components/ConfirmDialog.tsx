"use client";

import { useEffect, useRef } from "react";

type Props = {
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  description: string;
  confirmLabel: string;
  confirmClass?: string;
};

export default function ConfirmDialog({
  open,
  onConfirm,
  onCancel,
  title,
  description,
  confirmLabel,
  confirmClass = "bg-destructive text-on-destructive",
}: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open) el.showModal?.();
    else el.close?.();
  }, [open]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handler = () => onCancel();
    el.addEventListener("cancel", handler);
    return () => el.removeEventListener("cancel", handler);
  }, [onCancel]);

  return (
    <dialog
      ref={ref}
      className="rounded-2xl p-0 max-w-sm w-full border border-primary/20 shadow-[0_22px_60px_rgb(49_85_217/16%)] backdrop:bg-foreground/40 backdrop:backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === ref.current) onCancel();
      }}
    >
      <div className="p-6 font-sans">
        <h2 className="text-lg font-bold text-foreground mb-2">{title}</h2>
        <p className="text-sm text-foreground/70 mb-6">{description}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-xl border border-muted text-sm font-bold hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 rounded-xl text-sm font-bold min-h-[44px] ${confirmClass}`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
