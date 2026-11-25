"use client";

import { useState } from "react";
// One icon, not the barrel: the barrel made the first gallery test time out (5.3s vs 0.6s).
import { ArrowsClockwise } from "@phosphor-icons/react/dist/csr/ArrowsClockwise";

type Props = {
  /** The picture's link: undefined while it is being signed, null when there is none. */
  src: string | null | undefined;
  alt: string;
  /** Gets a new link. The caller drops the cached one first (`forgetSignedUrls`). Without it (no picture
   *  path to sign) the failed state has no Try again, since it could do nothing. */
  onRetry?: () => void;
  /** Box size and shape. Pictures are 1024×768, so the default box is 4:3. */
  className?: string;
  /** A small thumb: the failed state is one icon button instead of a line of text. */
  compact?: boolean;
};

/** A signed picture in a fixed box: pulse while it loads, fade in, and a failed state with Try again. */
export default function PictureBox({ src, alt, onRetry, className = "aspect-[4/3] w-full", compact = false }: Props) {
  // Keyed by URL, as on the shelf, so a new link pulses and fades in again.
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const [brokenSrc, setBrokenSrc] = useState<string | null>(null);
  const failed = src === null || (!!src && brokenSrc === src);
  const loaded = !!src && loadedSrc === src;

  function retry(event: React.MouseEvent) {
    // The box can sit in a clickable row or card; Try again must not open it.
    event.preventDefault();
    event.stopPropagation();
    setBrokenSrc(null);
    onRetry?.();
  }

  return (
    <div className={`relative overflow-hidden bg-muted ${className}`}>
      {!loaded && !failed && <div role="status" aria-label="Loading picture" className="absolute inset-0 animate-pulse bg-muted/50" />}
      {src && !failed && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={alt}
          loading="lazy"
          decoding="async"
          onLoad={() => setLoadedSrc(src)}
          onError={() => setBrokenSrc(src)}
          className={`relative h-full w-full object-cover transition-opacity duration-[var(--duration-slow)] ${loaded ? "opacity-100" : "opacity-0"}`}
        />
      )}
      {failed && !onRetry && (
        <p className="absolute inset-0 flex items-center justify-center p-1 text-center text-xs text-foreground/70">
          {compact ? <span className="sr-only">Picture didn&apos;t load</span> : "Picture didn't load"}
        </p>
      )}
      {failed && onRetry && (compact ? (
        <button type="button" onClick={retry}
          className="relative z-10 flex h-full min-h-11 w-full min-w-11 items-center justify-center text-foreground/60 hover:text-primary focus-visible:outline-3 focus-visible:outline-secondary">
          <ArrowsClockwise weight="bold" className="h-5 w-5" aria-hidden="true" />
          <span className="sr-only">Picture didn&apos;t load. Try again</span>
        </button>
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 p-3 text-center">
          <p className="text-sm text-foreground/70">Picture didn&apos;t load</p>
          <button type="button" onClick={retry}
            className="relative z-10 min-h-11 min-w-11 px-3 text-sm font-bold text-primary underline focus-visible:outline-3 focus-visible:outline-secondary">
            Try again
          </button>
        </div>
      ))}
    </div>
  );
}
