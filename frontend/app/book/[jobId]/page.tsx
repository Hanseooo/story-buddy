"use client";

import { use, useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

type Job = {
  id: string;
  caption: string | null;
  image_path: string | null;
};

const BUCKET = "storybook-images";

export default function BookPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const [job, setJob] = useState<Job | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const { data } = await supabase
        .from("jobs")
        .select("id, caption, image_path")
        .eq("id", jobId)
        .single();
      setJob(data);

      if (data?.image_path) {
        const { data: signed } = await supabase.storage
          .from(BUCKET)
          .createSignedUrl(data.image_path, 60 * 60);
        setImageUrl(signed?.signedUrl ?? null);
      }
    }
    load();
  }, [jobId]);

  if (!job) return <p>Loading your book...</p>;

  return (
    <div>
      {imageUrl && <img src={imageUrl} alt={job.caption ?? "storybook scene"} />}
      <p>{job.caption}</p>
    </div>
  );
}
