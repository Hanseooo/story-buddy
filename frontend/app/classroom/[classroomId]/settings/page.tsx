"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { createBrowserClient } from "@supabase/ssr";
import ConfirmDialog from "@/components/ConfirmDialog";

export default function ClassroomSettingsPage() {
  const { classroomId } = useParams<{ classroomId: string }>();
  const router = useRouter();
  const [classroom, setClassroom] = useState<{
    name: string;
    code: string;
  } | null>(null);
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleteInput, setDeleteInput] = useState("");
  const [toast, setToast] = useState<string | null>(null);

  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  useEffect(() => {
    supabase
      .from("classrooms")
      .select("name, code")
      .eq("id", classroomId)
      .single()
      .then(({ data }) => {
        if (data) {
          setClassroom(data);
          setNewName(data.name);
        }
      });
  }, [classroomId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function getToken() {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token;
  }

  async function handleRename(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const tok = await getToken();
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/classrooms/${classroomId}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${tok}`,
          },
          body: JSON.stringify({ name: newName.trim() }),
        }
      );
      setClassroom((c) => c && { ...c, name: newName.trim() });
      setToast("Classroom renamed");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    const tok = await getToken();
    await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/classrooms/${classroomId}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${tok}` },
      }
    );
    router.replace("/classroom");
  }

  if (!classroom) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-foreground/40 text-sm animate-pulse">
          Loading…
        </div>
      </div>
    );
  }

  const deleteArmed = deleteInput === classroom.name;

  return (
    <div className="p-6 sm:p-8 max-w-xl mx-auto">
      <h1 className="font-display text-2xl font-extrabold text-foreground mb-8">
        Classroom settings
      </h1>

      {/* Rename */}
      <section className="bg-surface border border-primary/15 rounded-2xl p-6 mb-6">
        <h2 className="font-bold text-foreground mb-4">Classroom name</h2>
        <form onSubmit={handleRename} className="flex gap-3">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
            className="flex-1 bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button
            type="submit"
            disabled={saving || newName.trim() === classroom.name}
            className="min-h-[44px] px-4 py-2 bg-primary text-on-primary rounded-xl text-sm font-bold disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </form>
      </section>

      {/* Class code (read-only) */}
      <section className="bg-surface border border-primary/15 rounded-2xl p-6 mb-6">
        <h2 className="font-bold text-foreground mb-1">Class code</h2>
        <p className="text-xs text-foreground/50 mb-3">
          This code never changes. Students use it to join your class.
        </p>
        <p className="font-mono text-xl font-bold tracking-widest text-primary">
          {classroom.code}
        </p>
      </section>

      {/* Danger zone */}
      <section className="bg-surface border border-destructive/30 rounded-2xl p-6">
        <h2 className="font-bold text-destructive mb-2">Danger zone</h2>
        <p className="text-sm text-foreground/60 mb-4">
          Deleting this classroom removes all its students and their books
          permanently.
        </p>
        <p className="text-sm font-bold text-foreground mb-2">
          Type{" "}
          <span className="font-mono">&ldquo;{classroom.name}&rdquo;</span> to
          confirm:
        </p>
        <input
          type="text"
          value={deleteInput}
          onChange={(e) => setDeleteInput(e.target.value)}
          placeholder={`Type "${classroom.name}"`}
          className="w-full bg-background border border-destructive/30 rounded-xl px-4 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-destructive/30"
        />
        <button
          onClick={() => setDeleteConfirm(true)}
          disabled={!deleteArmed}
          className="min-h-[44px] px-5 py-2 bg-destructive text-on-destructive rounded-xl text-sm font-bold disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Delete classroom
        </button>
      </section>

      <ConfirmDialog
        open={deleteConfirm}
        onCancel={() => setDeleteConfirm(false)}
        onConfirm={handleDelete}
        title="Delete classroom?"
        description={`This permanently deletes "${classroom.name}" and all student accounts. This cannot be undone.`}
        confirmLabel="Yes, delete"
        confirmClass="bg-destructive text-on-destructive"
      />

      {toast && (
        <div
          role="status"
          className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-foreground text-background px-5 py-3 rounded-xl text-sm font-bold shadow-lg z-50"
        >
          {toast}
        </div>
      )}
    </div>
  );
}
