"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { type Credential } from "@/lib/types";
import ConfirmDialog from "@/components/ConfirmDialog";

type Student = {
  id: string;
  nickname: string;
  display_nickname: string;
  removed_at: string | null;
};

export default function RosterPage() {
  const { classroomId } = useParams<{ classroomId: string }>();
  const router = useRouter();
  const [students, setStudents] = useState<Student[] | null>(null);
  const [classroom, setClassroom] = useState<{
    name: string;
    code: string;
  } | null>(null);
  const [removing, setRemoving] = useState<Student | null>(null);
  const [slip, setSlip] = useState<Credential | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  async function fetchRoster() {
    const [clsRes, studentsRes] = await Promise.all([
      supabase
        .from("classrooms")
        .select("name, code")
        .eq("id", classroomId)
        .single(),
      supabase
        .from("profiles")
        .select("id, nickname, display_nickname, removed_at")
        .eq("classroom_id", classroomId)
        .order("display_nickname"),
    ]);
    setClassroom(clsRes.data);
    setStudents(studentsRes.data ?? []);
  }

  useEffect(() => {
    fetchRoster();
  }, [classroomId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function callApi(path: string, method = "POST") {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    const resp = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
      method,
      headers: { Authorization: `Bearer ${session?.access_token}` },
    });
    if (!resp.ok) throw new Error(await resp.text());
    if (resp.status === 204) return null;
    return resp.json();
  }

  async function handleReset(student: Student) {
    try {
      const cred: Credential = await callApi(
        `/classrooms/${classroomId}/students/${student.id}/reset`
      );
      setSlip(cred);
      showToast(`Reset word for ${student.display_nickname}`);
    } catch {
      showToast("Could not reset — try again");
    }
  }

  async function handleRemove(student: Student) {
    try {
      await callApi(
        `/classrooms/${classroomId}/students/${student.id}/remove`
      );
      setRemoving(null);
      fetchRoster();
    } catch {
      showToast("Could not remove — try again");
    }
  }

  async function handleAddBack(student: Student) {
    try {
      const cred: Credential = await callApi(
        `/classrooms/${classroomId}/students/${student.id}/restore`
      );
      setSlip(cred);
      fetchRoster();
    } catch {
      showToast("Could not restore — try again");
    }
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  const active = students?.filter((s) => !s.removed_at) ?? [];
  const removed = students?.filter((s) => s.removed_at) ?? [];

  if (!students || !classroom) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-foreground/40 text-sm animate-pulse">
          Loading roster…
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 sm:p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end gap-4 mb-8">
        <div>
          <h1 className="font-display text-3xl font-extrabold text-foreground">
            {classroom.name}
          </h1>
          <p className="text-sm text-foreground/50 mt-1">
            Class code:{" "}
            <span className="font-mono font-bold text-foreground/80">
              {classroom.code}
            </span>
            {" · "}
            <button
              onClick={() => {
                navigator.clipboard.writeText(
                  `${window.location.origin}/join/${classroom.code}`
                );
                showToast("Join link copied");
              }}
              className="text-primary hover:underline"
            >
              Copy join link
            </button>
          </p>
        </div>
        <div className="sm:ml-auto flex gap-2">
          <button
            onClick={() => router.push(`/classroom/${classroomId}/add`)}
            className="min-h-[44px] px-5 py-2 bg-primary text-on-primary rounded-xl font-bold text-sm"
          >
            + Add students
          </button>
          <button
            onClick={() =>
              router.push(`/classroom/${classroomId}/settings`)
            }
            className="min-h-[44px] px-4 py-2 rounded-xl border border-primary/20 text-sm font-bold hover:bg-muted transition-colors"
          >
            Settings
          </button>
        </div>
      </div>

      {/* Active students: cards on mobile, table on sm+ */}
      {active.length === 0 ? (
        <div className="bg-surface border border-primary/15 rounded-2xl p-8 text-center text-foreground/50">
          <p className="font-bold mb-2">No students yet</p>
          <p className="text-sm">
            <button
              onClick={() => router.push(`/classroom/${classroomId}/add`)}
              className="text-primary hover:underline"
            >
              Add your first students
            </button>
          </p>
        </div>
      ) : (
        <>
          {/* Mobile cards */}
          <div className="sm:hidden space-y-3">
            {active.map((s) => (
              <StudentCard
                key={s.id}
                student={s}
                onReset={() => handleReset(s)}
                onRemove={() => setRemoving(s)}
              />
            ))}
          </div>

          {/* Desktop table */}
          <div className="hidden sm:block overflow-x-auto rounded-2xl border border-primary/15 shadow-[0_6px_18px_rgb(49_85_217/10%)]">
            <table className="w-full text-sm">
              <thead className="bg-surface border-b border-primary/10">
                <tr>
                  <th className="text-left px-6 py-3 font-bold text-foreground/60 text-xs uppercase tracking-wider">
                    Name
                  </th>
                  <th className="text-left px-6 py-3 font-bold text-foreground/60 text-xs uppercase tracking-wider">
                    Login nickname
                  </th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-primary/10 bg-surface">
                {active.map((s) => (
                  <StudentRow
                    key={s.id}
                    student={s}
                    onReset={() => handleReset(s)}
                    onRemove={() => setRemoving(s)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Removed students (collapsible) */}
      {removed.length > 0 && (
        <details className="mt-8">
          <summary className="cursor-pointer text-sm font-bold text-foreground/50 hover:text-foreground/80 transition-colors list-none flex items-center gap-2">
            <span>▸</span> Removed ({removed.length})
          </summary>
          <div className="mt-3 space-y-2">
            {removed.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between px-4 py-3 bg-surface/50 border border-primary/10 rounded-xl text-sm text-foreground/60"
              >
                <span className="font-bold">{s.display_nickname}</span>
                <button
                  onClick={() => handleAddBack(s)}
                  className="text-primary text-xs font-bold hover:underline min-h-[44px] px-2"
                >
                  Add back
                </button>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Confirm remove dialog */}
      <ConfirmDialog
        open={!!removing}
        onCancel={() => setRemoving(null)}
        onConfirm={() => removing && handleRemove(removing)}
        title={`Remove ${removing?.display_nickname}?`}
        description="They won't be able to log in. Their books are safe. You can add them back later."
        confirmLabel="Remove"
        confirmClass="bg-destructive text-on-destructive"
      />

      {/* One-slip modal after reset/restore */}
      {slip && (
        <div className="fixed inset-0 bg-foreground/40 backdrop-blur-sm z-40 flex items-center justify-center p-4">
          <div className="bg-surface rounded-2xl p-6 max-w-sm w-full border border-primary/20 shadow-[0_22px_60px_rgb(49_85_217/16%)]">
            <h2 className="font-display text-xl font-bold mb-1">Word reset</h2>
            <p className="text-sm text-foreground/60 mb-4">
              Give this to {slip.display_nickname}. It won&apos;t be shown
              again.
            </p>
            <div className="bg-background rounded-xl p-4 mb-4 text-center">
              <p className="text-xs text-foreground/50 mb-1">Class code</p>
              <p className="font-mono font-bold text-lg">{classroom.code}</p>
              <p className="text-xs text-foreground/50 mt-3 mb-1">Nickname</p>
              <p className="font-mono font-bold text-lg">{slip.nickname}</p>
              <p className="text-xs text-foreground/50 mt-3 mb-1">Word</p>
              <p className="font-mono font-bold text-2xl text-primary">
                {slip.password}
              </p>
            </div>
            <button
              onClick={() => setSlip(null)}
              className="w-full min-h-[44px] bg-muted rounded-xl font-bold text-sm"
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          role="status"
          className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-foreground text-background px-5 py-3 rounded-xl text-sm font-bold shadow-lg z-50 transition-opacity"
        >
          {toast}
        </div>
      )}
    </div>
  );
}

function StudentCard({
  student,
  onReset,
  onRemove,
}: {
  student: Student;
  onReset: () => void;
  onRemove: () => void;
}) {
  return (
    <div className="bg-surface border border-primary/15 rounded-2xl p-4 flex items-center justify-between gap-3">
      <div>
        <p className="font-bold text-foreground">{student.display_nickname}</p>
        <p className="text-xs font-mono text-foreground/50 mt-0.5">
          @{student.nickname}
        </p>
      </div>
      <RowMenu onReset={onReset} onRemove={onRemove} />
    </div>
  );
}

function StudentRow({
  student,
  onReset,
  onRemove,
}: {
  student: Student;
  onReset: () => void;
  onRemove: () => void;
}) {
  return (
    <tr className="hover:bg-background/40 transition-colors">
      <td className="px-6 py-3 font-bold">{student.display_nickname}</td>
      <td className="px-6 py-3 font-mono text-foreground/60 text-xs">
        {student.nickname}
      </td>
      <td className="px-6 py-3 text-right">
        <RowMenu onReset={onReset} onRemove={onRemove} />
      </td>
    </tr>
  );
}

function RowMenu({
  onReset,
  onRemove,
}: {
  onReset: () => void;
  onRemove: () => void;
}) {
  const id = useRef(`menu-${Math.random().toString(36).slice(2)}`).current;
  return (
    <div className="relative inline-block">
      <button
        // @ts-expect-error — popover API not yet in React types
        popovertarget={id}
        className="min-h-[44px] w-11 flex items-center justify-center rounded-xl hover:bg-muted transition-colors text-foreground/60 font-bold"
        aria-label="Student actions"
      >
        ⋮
      </button>
      <div
        id={id}
        // @ts-expect-error — popover API not yet in React types
        popover="auto"
        className="absolute right-0 mt-1 bg-surface border border-primary/20 rounded-xl shadow-[0_10px_28px_rgb(49_85_217/12%)] p-1 min-w-[140px] z-20"
      >
        <button
          onClick={() => {
            onReset();
            (
              document.getElementById(id) as HTMLElement & {
                hidePopover: () => void;
              }
            )?.hidePopover();
          }}
          className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-muted transition-colors font-bold"
        >
          Reset word
        </button>
        <button
          onClick={() => {
            onRemove();
            (
              document.getElementById(id) as HTMLElement & {
                hidePopover: () => void;
              }
            )?.hidePopover();
          }}
          className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-muted transition-colors font-bold text-destructive"
        >
          Remove
        </button>
      </div>
    </div>
  );
}
