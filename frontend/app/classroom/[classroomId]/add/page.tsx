"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import {
  computePreview,
  type Preset,
} from "@/lib/classroom-preview";
import { normalizeNickname } from "@/lib/nickname";
import { type Credential } from "@/lib/types";

type RejectedRow = {
  display_nickname: string;
  reason: string;
};

type Phase = "paste" | "preview" | "slips";

const PRESET_LABELS: Record<Preset, string> = {
  first: "First name only",
  "first-last-initial": "First + last initial",
  full: "Full name",
};

export default function AddStudentsPage() {
  const { classroomId } = useParams<{ classroomId: string }>();
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("paste");
  const [paste, setPaste] = useState("");
  const [preset, setPreset] = useState<Preset>("first");
  const [overrides, setOverrides] = useState<Record<number, string>>({});
  const [existingNicknames, setExistingNicknames] = useState<Set<string>>(new Set());
  const [classroom, setClassroom] = useState<{ name: string; code: string } | null>(null);
  const [created, setCreated] = useState<Credential[]>([]);
  const [rejected, setRejected] = useState<RejectedRow[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [singleName, setSingleName] = useState("");
  const [singleSubmitting, setSingleSubmitting] = useState(false);
  const [copyDone, setCopyDone] = useState(false);

  // Fetch classroom + existing nicknames for collision check
  useEffect(() => {
    Promise.all([
      supabase.from("classrooms").select("name, code").eq("id", classroomId).single(),
      supabase.from("profiles").select("nickname").eq("classroom_id", classroomId),
    ]).then(([clsRes, studRes]) => {
      setClassroom(clsRes.data);
      setExistingNicknames(
        new Set((studRes.data ?? []).map((s: { nickname: string }) => s.nickname))
      );
    });
  }, [classroomId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Derive preview rows purely — no effect needed, computePreview is fast and pure
  const previewRows = useMemo(
    () => computePreview(paste.split("\n"), existingNicknames, preset),
    [paste, existingNicknames, preset]
  );

  // beforeunload guard while slips are showing (test 18)
  useEffect(() => {
    if (phase !== "slips") return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [phase]);

  const getToken = useCallback(async () => {
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token;
  }, []);

  async function postStudents(students: { display_nickname: string }[]) {
    const tok = await getToken();
    const resp = await fetch(
      `${process.env.NEXT_PUBLIC_API_BASE_URL}/classrooms/${classroomId}/students`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${tok}`,
        },
        body: JSON.stringify({ students }),
      }
    );
    if (!resp.ok) throw new Error(await resp.text());
    return resp.json() as Promise<{ created: Credential[]; rejected: RejectedRow[] }>;
  }

  async function handleSubmitBulk() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const students = previewRows.map((row, i) => ({
        display_nickname: overrides[i] ?? row.displayNickname,
      }));
      const body = await postStudents(students);
      setCreated(body.created);
      setRejected(body.rejected);
      setPhase("slips");
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Something went wrong — try again");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmitSingle(e: React.FormEvent) {
    e.preventDefault();
    setSingleSubmitting(true);
    try {
      const body = await postStudents([{ display_nickname: singleName.trim() }]);
      setCreated(body.created);
      setRejected(body.rejected);
      setPhase("slips");
    } catch {
      // ponytail: single-student errors are rare; a toast is overkill for now
    } finally {
      setSingleSubmitting(false);
    }
  }

  function handleLeaveSlips() {
    setPhase("paste");
    router.push(`/classroom/${classroomId}`);
  }

  async function handleCopyAll() {
    const slipsText = created
      .map(
        (s) =>
          `Class code: ${classroom?.code}\nName: ${s.display_nickname}\nNickname: ${s.nickname}\nWord: ${s.password}`
      )
      .join("\n\n---\n\n");
    await navigator.clipboard.writeText(slipsText);
    setCopyDone(true);
    setTimeout(() => setCopyDone(false), 2000);
  }

  // ── Phase C: Slips ────────────────────────────────────────────────────────

  if (phase === "slips") {
    return (
      <div className="p-6 sm:p-8 max-w-4xl mx-auto">
        <div
          className="bg-warning/10 border border-warning/30 rounded-2xl p-4 mb-6 text-sm font-bold text-warning"
          role="alert"
        >
          Print or save now — these words are not shown again. You can reset any
          student&apos;s word later.
        </div>

        {rejected.length > 0 && (
          <div className="bg-surface border border-destructive/20 rounded-2xl p-4 mb-6">
            <p className="font-bold text-destructive mb-2">
              {rejected.length} name{rejected.length > 1 ? "s" : ""} could not be created:
            </p>
            <ul className="text-sm text-foreground/70 list-disc list-inside mb-3">
              {rejected.map((r, i) => (
                <li key={i}>
                  <span className="font-bold">{r.display_nickname}</span> — {r.reason}
                </li>
              ))}
            </ul>
            <p className="text-xs text-foreground/60 mb-2">Fix and paste again:</p>
            <textarea
              className="w-full bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm font-mono h-24 focus:outline-none focus:ring-2 focus:ring-primary/30"
              defaultValue={rejected.map((r) => r.display_nickname).join("\n")}
              readOnly
            />
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col-reverse sm:flex-row gap-3 mb-6">
          <button
            onClick={handleCopyAll}
            className="min-h-[44px] flex-1 bg-surface border border-primary/20 rounded-xl text-sm font-bold hover:bg-muted transition-colors"
          >
            {copyDone ? "Copied!" : "Copy all as text"}
          </button>
          <button
            onClick={() => window.print()}
            className="min-h-[44px] flex-1 bg-primary text-on-primary rounded-xl text-sm font-bold"
          >
            Print
          </button>
        </div>

        {/* Slips grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 print:grid-cols-2 print:gap-2">
          {created.map((s) => (
            <div
              key={s.profile_id}
              className="bg-surface border border-primary/20 rounded-2xl p-4 print:rounded-lg print:p-2"
            >
              <p className="text-xs text-foreground/50 mb-0.5">Class code</p>
              <p className="font-mono font-bold text-sm mb-3">{classroom?.code}</p>
              <p className="text-xs text-foreground/50 mb-0.5">Name</p>
              <p className="font-bold mb-3">{s.display_nickname}</p>
              <p className="text-xs text-foreground/50 mb-0.5">Login nickname</p>
              <p className="font-mono text-sm mb-3">{s.nickname}</p>
              <p className="text-xs text-foreground/50 mb-0.5">Word</p>
              <p className="font-mono font-extrabold text-xl text-primary">{s.password}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 text-center">
          <button
            onClick={handleLeaveSlips}
            className="text-sm text-foreground/50 hover:text-foreground underline"
          >
            Done — go back to roster
          </button>
        </div>
      </div>
    );
  }

  // ── Phase B: Preview ───────────────────────────────────────────────────────

  if (phase === "preview") {
    const hasUnresolvedErrors = previewRows.some((r) => r.editable && !overrides[previewRows.indexOf(r)]);

    return (
      <div className="p-6 sm:p-8 max-w-3xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => setPhase("paste")}
            className="text-sm text-foreground/50 hover:text-foreground transition-colors"
          >
            ← Back
          </button>
          <h1 className="font-display text-2xl font-extrabold text-foreground">
            Preview ({previewRows.length}{" "}
            {previewRows.length === 1 ? "student" : "students"})
          </h1>
        </div>

        <div className="bg-surface border border-primary/15 rounded-2xl overflow-hidden mb-6 shadow-[0_6px_18px_rgb(49_85_217/10%)]">
          <table className="w-full text-sm">
            <thead className="bg-background border-b border-primary/10">
              <tr>
                <th className="text-left px-4 py-3 font-bold text-foreground/60 text-xs uppercase tracking-wider">
                  Shown to classmates
                </th>
                <th className="text-left px-4 py-3 font-bold text-foreground/60 text-xs uppercase tracking-wider">
                  Login nickname
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary/10">
              {previewRows.map((row, i) => {
                const override = overrides[i] ?? "";
                let derivedNick = row.nickname;
                if (row.editable && override) {
                  try {
                    derivedNick = normalizeNickname(override.replace(/\s*\.$/, ""));
                  } catch {
                    derivedNick = "—";
                  }
                }
                const unresolved = row.editable && !override;

                return (
                  <tr key={i} className={unresolved ? "bg-warning/5" : ""}>
                    <td className="px-4 py-3">
                      {row.editable ? (
                        <div>
                          <input
                            type="text"
                            defaultValue={row.suggestion ?? row.displayNickname}
                            onChange={(e) =>
                              setOverrides((o) => ({ ...o, [i]: e.target.value }))
                            }
                            placeholder="Edit name"
                            className="bg-background border border-warning/40 rounded-lg px-3 py-1.5 text-sm w-full focus:outline-none focus:ring-2 focus:ring-warning/30"
                            aria-label={`Edit name for row ${i + 1}`}
                          />
                          {row.reason && (
                            <p className="text-xs text-warning/80 mt-1">{row.reason}</p>
                          )}
                        </div>
                      ) : (
                        <span className="font-bold">{row.displayNickname}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-foreground/60 text-xs">
                      {derivedNick}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {submitError && (
          <p className="text-destructive text-sm mb-3" role="alert">
            {submitError}
          </p>
        )}
        {hasUnresolvedErrors && (
          <p className="text-warning text-sm mb-3" role="alert">
            Fix the highlighted rows before creating accounts.
          </p>
        )}

        <button
          onClick={handleSubmitBulk}
          disabled={submitting || hasUnresolvedErrors}
          className="min-h-[44px] w-full bg-primary text-on-primary rounded-xl font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          {submitting
            ? "Creating accounts…"
            : `Create ${previewRows.length} account${previewRows.length === 1 ? "" : "s"}`}
        </button>
      </div>
    );
  }

  // ── Phase A: Paste ─────────────────────────────────────────────────────────

  const lineCount = paste.split("\n").filter((l) => l.trim()).length;

  return (
    <div className="p-6 sm:p-8 max-w-3xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => router.push(`/classroom/${classroomId}`)}
          className="text-sm text-foreground/50 hover:text-foreground transition-colors"
        >
          ← Roster
        </button>
        <h1 className="font-display text-2xl font-extrabold text-foreground">
          Add students
        </h1>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-5 gap-6">
        {/* Bulk paste — 3/5 columns on sm+ */}
        <div className="sm:col-span-3">
          <div className="mb-4">
            <p className="text-sm font-bold text-foreground mb-2">Shown to classmates</p>
            <div className="flex gap-2 flex-wrap">
              {(Object.keys(PRESET_LABELS) as Preset[]).map((p) => (
                <button
                  key={p}
                  onClick={() => setPreset(p)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors ${
                    preset === p
                      ? "bg-primary text-on-primary border-primary"
                      : "bg-surface border-primary/20 hover:bg-muted"
                  }`}
                >
                  {PRESET_LABELS[p]}
                </button>
              ))}
            </div>
          </div>

          <label className="block text-sm font-bold text-foreground mb-2" htmlFor="paste-input">
            Paste class list (one name per line)
          </label>
          <textarea
            id="paste-input"
            value={paste}
            onChange={(e) => setPaste(e.target.value)}
            placeholder={"Juan Dela Cruz\nMaria Santos\nAna Reyes"}
            rows={10}
            className="w-full bg-background border border-primary/20 rounded-xl px-4 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/30 resize-y"
          />
          <button
            onClick={() => {
              if (lineCount > 0) {
                setOverrides({});
                setPhase("preview");
              }
            }}
            disabled={lineCount === 0}
            className="mt-4 min-h-[44px] w-full bg-primary text-on-primary rounded-xl font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            Preview{lineCount > 0 ? ` (${lineCount} student${lineCount === 1 ? "" : "s"})` : ""}
          </button>
        </div>

        {/* Single-student quick add — 2/5 columns on sm+ */}
        <div className="sm:col-span-2 border-t sm:border-t-0 sm:border-l border-primary/10 pt-6 sm:pt-0 sm:pl-6">
          <p className="text-sm font-bold text-foreground mb-1">Add one student</p>
          <p className="text-xs text-foreground/50 mb-4">
            For latecomers. Skips the preview.
          </p>
          <form onSubmit={handleSubmitSingle} className="space-y-3">
            <input
              type="text"
              value={singleName}
              onChange={(e) => setSingleName(e.target.value)}
              placeholder="e.g. Juan D."
              className="w-full bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              aria-label="Single student name"
            />
            <button
              type="submit"
              disabled={!singleName.trim() || singleSubmitting}
              className="min-h-[44px] w-full bg-surface border border-primary/20 rounded-xl text-sm font-bold hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {singleSubmitting ? "Adding…" : "Add student"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
