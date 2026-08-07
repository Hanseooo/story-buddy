"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createBrowserClient } from "@supabase/ssr";

type Classroom = { id: string; name: string; code: string };

export default function ClassroomPickerPage() {
  const router = useRouter();
  const [classrooms, setClassrooms] = useState<Classroom[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return;
      supabase
        .from("classrooms")
        .select("id, name, code")
        .eq("owner_id", user.id)
        .order("created_at")
        .then(({ data }) => {
          const list = data ?? [];
          if (list.length === 1) {
            router.replace(`/classroom/${list[0].id}`);
          } else {
            setClassrooms(list);
          }
        });
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const {
      data: { session },
    } = await supabase.auth.getSession();
    const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/classrooms`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session?.access_token}`,
      },
      body: JSON.stringify({ name: name.trim() }),
    });
    if (!resp.ok) {
      setError("Could not create classroom. Try again.");
      return;
    }
    const cls = await resp.json();
    router.push(`/classroom/${cls.id}`);
  }

  if (classrooms === null) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-foreground/40 text-sm animate-pulse">
          Loading…
        </div>
      </div>
    );
  }

  if (classrooms.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] p-6">
        <div className="max-w-sm w-full bg-surface border border-primary/20 rounded-2xl p-8 shadow-[0_10px_28px_rgb(49_85_217/12%)]">
          <h1 className="font-display text-2xl font-extrabold text-foreground mb-2">
            Create your first classroom
          </h1>
          <p className="text-sm text-foreground/60 mb-6">
            Give your class a name to get started.
          </p>
          <form onSubmit={handleCreate} className="space-y-4">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Grade 3 – Alon"
              required
              className="w-full bg-background border border-primary/20 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            {error && (
              <p className="text-destructive text-sm" role="alert">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={!name.trim()}
              className="w-full min-h-[44px] bg-primary text-on-primary rounded-xl font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create classroom
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 sm:p-8 max-w-4xl mx-auto">
      <div className="flex items-end justify-between mb-8">
        <h1 className="font-display text-3xl font-extrabold text-foreground">
          Your classrooms
        </h1>
        <button
          onClick={() => setCreating(true)}
          className="min-h-[44px] px-5 py-2 bg-primary text-on-primary rounded-xl font-bold text-sm"
        >
          + New classroom
        </button>
      </div>

      {creating && (
        <div className="mb-6 bg-surface border border-primary/20 rounded-xl p-4">
          <form onSubmit={handleCreate} className="flex gap-3 items-center">
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Classroom name"
              className="flex-1 bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
            <button
              type="submit"
              disabled={!name.trim()}
              className="min-h-[44px] px-4 py-2 bg-primary text-on-primary rounded-xl font-bold text-sm disabled:opacity-50"
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setCreating(false)}
              className="min-h-[44px] px-4 py-2 rounded-xl border border-muted text-sm font-bold hover:bg-muted"
            >
              Cancel
            </button>
          </form>
          {error && (
            <p className="text-destructive text-sm mt-2" role="alert">
              {error}
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {classrooms.map((c) => (
          <button
            key={c.id}
            onClick={() => router.push(`/classroom/${c.id}`)}
            className="text-left bg-surface border border-primary/15 rounded-2xl p-6 shadow-[0_6px_18px_rgb(49_85_217/10%)] hover:-translate-y-0.5 transition-transform focus:outline-none focus:ring-2 focus:ring-primary/30"
          >
            <p className="font-bold text-lg text-foreground mb-1">{c.name}</p>
            <p className="text-sm font-mono text-foreground/50">{c.code}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
