"use client";

import {useEffect, useState} from "react";
import {forgetSignedUrls, signPaths, type ImageJob} from "@/lib/signedUrls";
import PictureBox from "@/components/PictureBox";

/** A book's cover, signed only through `signPaths` with its job. `src` is a link the server already signed. */
export default function GuardedCover({job, alt, src, className}: {job: ImageJob; alt: string; src?: string; className?: string}) {
  const path = job.pages?.[0]?.image_path;
  const [url, setUrl] = useState<string | null | undefined>(src);
  const [attempt, setAttempt] = useState(0);
  // A refreshed server render can pass a newly signed link; follow it.
  const [prevSrc, setPrevSrc] = useState(src);
  if (src !== prevSrc) {
    setPrevSrc(src);
    setUrl(src);
    setAttempt(0);
  }
  useEffect(() => {
    if (!path || (src && attempt === 0)) return;
    const controller = new AbortController();
    signPaths([path], [job], controller.signal).then((urls) => {
      if (!controller.signal.aborted) setUrl(urls[path] ?? null);
    }, () => {
      if (!controller.signal.aborted) setUrl(null);
    });
    return () => { controller.abort(); };
  }, [job, path, src, attempt]);
  return <PictureBox src={path ? url : null} alt={alt} className={className} onRetry={path ? () => {
    forgetSignedUrls([path]);
    setUrl(undefined);
    setAttempt(value => value + 1);
  } : undefined} />;
}
