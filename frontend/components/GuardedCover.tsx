"use client";

import {useEffect, useState} from "react";
import {signPaths, type ImageJob} from "@/lib/signedUrls";

export default function GuardedCover({job, alt}: {job: ImageJob; alt: string}) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const path = job.pages?.[0]?.image_path;
    if (path) void signPaths([path], [job], controller.signal).then((urls) => {
      if (controller.signal.aborted) return;
      setUrl(urls[path] ?? null);
      setFailed(!urls[path]);
    });
    return () => { controller.abort(); };
  }, [job, retry]);
  if (url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt={alt} loading="lazy" className="aspect-[3/4] w-full border-b border-primary/15 bg-muted object-cover" />;
  }
  return <div className="flex aspect-[3/4] w-full items-center justify-center bg-muted p-3 text-center" role="status">
    {failed ? <span>Picture unavailable</span> : <span>Loading picture…</span>}
    {failed && <button type="button" className="min-h-11 underline" onClick={(event) => {
      event.preventDefault(); setFailed(false); setRetry(value => value + 1);
    }}>Try loading again</button>}
  </div>;
}
