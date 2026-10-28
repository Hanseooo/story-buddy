"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import ConfirmDialog from "@/components/ConfirmDialog";
import Link from "next/link";
import { ArrowLeft } from "@phosphor-icons/react";

type ThemeSettings = {
  theme_ids: string[];
  settings_version: number;
  editable: boolean;
  themes: { id: string; name: string; trigger: string; exception: string }[];
};

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
  const [themes, setThemes] = useState<ThemeSettings | null>(null);
  const [themeIds, setThemeIds] = useState<string[]>([]);
  const [themeLoading, setThemeLoading] = useState(true);
  const [themeError, setThemeError] = useState<string | null>(null);
  const [themeSaving, setThemeSaving] = useState(false);
  const [themeSaved, setThemeSaved] = useState(false);
  const [themeLoadAttempt, setThemeLoadAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    async function load() {
      setThemeLoading(true);
      setThemeError(null);
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/teacher/classrooms/${classroomId}/moderation-settings`, {
          headers: { Authorization: `Bearer ${session?.access_token}` }, cache: "no-store",
        });
        if (!response.ok) throw new Error("settings unavailable");
        const saved: ThemeSettings = await response.json();
        if (active) { setThemes(saved); setThemeIds(saved.theme_ids); }
      } catch {
        if (active) setThemeError("Could not load review themes. Try again.");
      } finally {
        if (active) setThemeLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [classroomId, themeLoadAttempt]);

  async function saveThemes(e: React.FormEvent) {
    e.preventDefault();
    if (!themes || themeSaving) return;
    setThemeSaving(true);
    setThemeSaved(false);
    setThemeError(null);
    try {
      const tok = await getToken();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/teacher/classrooms/${classroomId}/moderation-settings`, {
        method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${tok}` },
        body: JSON.stringify({ expected_version: themes.settings_version, theme_ids: themeIds }),
      });
      if (!response.ok) {
        if (response.status === 409) {
          const conflict = (await response.json()).detail;
          if (conflict?.code === "settings_changed") {
            setThemes({ ...themes, settings_version: conflict.settings_version, theme_ids: conflict.theme_ids });
            setThemeError("Settings changed on another device. Your choices are kept. Review them and retry saving.");
            return;
          }
          if (conflict === "settings_disabled") {
            setThemes({ ...themes, editable: false });
            setThemeError("Review theme editing is currently unavailable. Your choices are kept.");
            return;
          }
        }
        throw new Error("save failed");
      }
      const saved = await response.json();
      setThemes({ ...themes, ...saved });
      setThemeIds(saved.theme_ids);
      setThemeSaved(true);
    } catch {
      setThemeError("Could not save review themes. Your choices are kept. Try again.");
    } finally {
      setThemeSaving(false);
    }
  }

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
  }, [classroomId]);

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
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/classrooms/${classroomId}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${tok}`,
          },
          body: JSON.stringify({ name: newName.trim() }),
        }
      );
      if (!res.ok) {
        setToast("Could not rename — try again");
        return;
      }
      setClassroom((c) => c && { ...c, name: newName.trim() });
      setToast("Classroom renamed");
    } catch {
      setToast("Could not rename — try again");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    let ok = false;
    try {
      const tok = await getToken();
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/classrooms/${classroomId}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${tok}` },
        }
      );
      ok = res.ok;
    } catch {
      // Network failure: fall through to the same not-deleted state as a non-2xx.
    }
    if (!ok) {
      // Navigating away here would show the teacher a classroom list that still has it.
      // Close the modal first: while it is open the rest of the page is inert, so the
      // toast would sit unreadable behind its backdrop.
      setDeleteConfirm(false);
      setToast("Could not delete — try again");
      return;
    }
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
      <Link
        href={`/classroom/${classroomId}`}
        className="inline-flex items-center gap-2 text-sm font-bold text-foreground/60 hover:text-primary transition-colors mb-6"
      >
        <ArrowLeft weight="bold" className="w-4 h-4" />
        Back to Roster
      </Link>
      
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

      <section aria-labelledby="review-themes-heading" className="bg-surface border border-primary/15 rounded-2xl p-6 mb-6">
        <h2 id="review-themes-heading" className="font-bold text-foreground mb-2">Optional classroom review themes</h2>
        <p id="review-themes-help" className="text-sm text-foreground/70 mb-4">
          Enabled themes request one teacher review of the submitted story before pictures are made.
          They do not reject a story or label it unsafe. Changes apply to new submissions only.
          Existing stories keep their captured settings and any review already waiting.
        </p>
        <p className="text-sm text-foreground/70 mb-4">
          Turning a theme off removes only that extra review. Shared safety checks still apply to every story and picture.
        </p>
        {themeLoading && <p role="status">Loading review themes…</p>}
        {themeError && <p role="alert" className="text-sm text-destructive mb-3">{themeError}</p>}
        {!themeLoading && !themes && <button type="button" className="min-h-[44px] font-bold text-primary"
          onClick={() => setThemeLoadAttempt(value => value + 1)}>Retry loading review themes</button>}
        {themes && <form onSubmit={saveThemes}>
          {!themes.editable && <p className="text-sm text-foreground/70 mb-3">Review theme editing is currently unavailable.</p>}
          <fieldset disabled={!themes.editable || themeSaving} aria-describedby="review-themes-help" className="space-y-4 disabled:opacity-60">
            <legend className="sr-only">Themes requiring teacher review</legend>
            {themes.themes.map(theme => <label key={theme.id} className="flex items-start gap-3 min-h-[44px] cursor-pointer">
              <input type="checkbox" checked={themeIds.includes(theme.id)} className="mt-1 w-5 h-5 accent-primary focus-visible:outline-2 focus-visible:outline-primary"
                onChange={e => {
                  setThemeIds(ids => e.target.checked ? [...ids, theme.id] : ids.filter(id => id !== theme.id));
                  setThemeSaved(false);
                }} />
              <span className="min-w-0"><span className="block text-sm font-bold">{theme.name}</span>
                <span className="block text-sm text-foreground/70 mt-1">{theme.trigger}</span>
                <span className="block text-xs text-foreground/60 mt-1">Does not include: {theme.exception}</span>
              </span>
            </label>)}
          </fieldset>
          <button type="submit" disabled={!themes.editable || themeSaving || (!themeError && themeIds.length === themes.theme_ids.length && themeIds.every(id => themes.theme_ids.includes(id)))}
            className="mt-5 min-h-[44px] px-4 py-2 bg-primary text-on-primary rounded-xl text-sm font-bold disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
            {themeSaving ? "Saving review themes…" : themeError ? "Retry saving review themes" : "Save review themes"}
          </button>
          {themeSaved && <p role="status" className="mt-3 text-sm text-success">Review themes saved</p>}
        </form>}
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
