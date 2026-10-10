"use client";

import { useRef, useState } from "react";
import { ImageBroken, X } from "@phosphor-icons/react";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

export default function ImageViewer({
  src,
  alt,
  className = "",
}: {
  src: string | null;
  alt: string;
  className?: string;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const placeholderRef = useRef<HTMLDivElement>(null);
  const [broken, setBroken] = useState(false);
  const [enlargedBroken, setEnlargedBroken] = useState(false);

  const placeholder = (
    <div
      ref={placeholderRef}
      tabIndex={-1}
      role="img"
      aria-label={alt}
      className={`flex flex-col items-center justify-center gap-1 rounded-xl bg-muted/40 text-foreground/50 ${FOCUS} ${className}`}
    >
      <ImageBroken weight="duotone" className="size-8" aria-hidden />
      <span className="px-2 text-center text-xs font-medium">Image unavailable</span>
    </div>
  );

  if (!src) return placeholder;

  function closeDialog() {
    dialogRef.current?.close();
    if (broken) placeholderRef.current?.focus();
    else triggerRef.current?.focus();
  }

  return (
    <>
      {broken ? placeholder : (
        <button
          ref={triggerRef}
          type="button"
          aria-label={`Enlarge ${alt}`}
          onClick={() => dialogRef.current?.showModal()}
          className={`block min-h-11 min-w-11 overflow-hidden rounded-xl bg-muted/30 ${FOCUS} ${className}`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={src} alt={alt} onError={() => setBroken(true)} className="size-full object-cover" />
        </button>
      )}
      <dialog
        ref={dialogRef}
        aria-label={alt}
        onCancel={(event) => {
          event.preventDefault();
          closeDialog();
        }}
        onClick={(event) => {
          if (event.target === dialogRef.current) closeDialog();
        }}
        className="m-auto max-h-[92dvh] max-w-[92vw] rounded-2xl bg-surface p-0 backdrop:bg-foreground/60 backdrop:backdrop-blur-sm"
      >
        <div className="relative">
          <button
            type="button"
            aria-label="Close image"
            onClick={closeDialog}
            className={`absolute right-2 top-2 inline-flex size-11 items-center justify-center rounded-full bg-surface/90 neo-border ${FOCUS}`}
          >
            <X weight="bold" className="size-5" aria-hidden />
          </button>
          {enlargedBroken ? (
            <div role="img" aria-label={alt} className="flex min-h-64 min-w-56 items-center justify-center px-5 text-sm text-foreground/70">
              Image unavailable
            </div>
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={src} alt={alt} onError={() => setEnlargedBroken(true)} className="block max-h-[90dvh] w-auto max-w-full" />
          )}
        </div>
      </dialog>
    </>
  );
}
