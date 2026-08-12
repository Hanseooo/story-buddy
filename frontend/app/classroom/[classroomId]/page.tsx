"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { type Credential } from "@/lib/types";
import ConfirmDialog from "@/components/ConfirmDialog";
import { Avatar } from "@/components/Avatar";
import { motion } from "framer-motion";

type Student = {
  id: string;
  nickname: string;
  display_nickname: string;
  removed_at: string | null;
  avatar_id: string | null;
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
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  async function fetchRoster() {
    const [clsRes, studentsRes] = await Promise.all([
      supabase
        .from("classrooms")
        .select("name, code")
        .eq("id", classroomId)
        .single(),
      supabase
        .from("profiles")
        .select("id, nickname, display_nickname, removed_at, avatar_id")
        .eq("classroom_id", classroomId)
        .order("display_nickname"),
    ]);
    setClassroom(clsRes.data);
    setStudents(studentsRes.data ?? []);
  }

  useEffect(() => {
    async function load() {
      const [clsRes, studentsRes] = await Promise.all([
        supabase
          .from("classrooms")
          .select("name, code")
          .eq("id", classroomId)
          .single(),
        supabase
          .from("profiles")
          .select("id, nickname, display_nickname, removed_at, avatar_id")
          .eq("classroom_id", classroomId)
          .order("display_nickname"),
      ]);
      setClassroom(clsRes.data);
      setStudents(studentsRes.data ?? []);
    }
    void load();
  }, [classroomId]);

  async function callApi(path: string, method = "POST") {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    const resp = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}${path}`, {
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
        <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center animate-stepper-pulse">
          <span className="text-2xl">👥</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 sm:p-8 max-w-5xl mx-auto min-h-[calc(100vh-80px)] pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end gap-6 mb-10 border-b-2 border-primary/5 pb-6">
        <div>
          <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
            {classroom.name}
          </h1>
          <div className="flex flex-wrap items-center gap-3 mt-3">
            <span className="inline-flex items-center gap-2 bg-surface px-3 py-1.5 rounded-lg border-2 border-primary/5">
              <span className="text-xs font-bold text-foreground/50 uppercase tracking-wider">Class code</span>
              <span className="text-sm font-mono font-bold text-primary">{classroom.code}</span>
            </span>
            <button
              onClick={() => {
                navigator.clipboard.writeText(
                  `${window.location.origin}/join/${classroom.code}`
                );
                showToast("Join link copied");
              }}
              className="text-sm font-bold text-primary hover:text-primary-deep hover:underline transition-colors"
            >
              Copy join link
            </button>
          </div>
        </div>
        <div className="sm:ml-auto flex gap-3">
          <motion.button
            whileTap={{ y: 4, boxShadow: "0 0px 0 var(--color-primary-deep)" }}
            onClick={() => router.push(`/classroom/${classroomId}/add`)}
            className="min-h-[48px] px-6 bg-primary text-on-primary rounded-xl font-bold text-sm shadow-[0_4px_0_var(--color-primary-deep)] transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
          >
            + Add students
          </motion.button>
          <motion.button
            whileTap={{ scale: 0.96 }}
            onClick={() => router.push(`/classroom/${classroomId}/settings`)}
            className="min-h-[48px] w-12 flex items-center justify-center rounded-xl border-2 border-primary/10 text-foreground/70 font-bold hover:bg-muted transition-colors bg-surface focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
            aria-label="Settings"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
          </motion.button>
        </div>
      </div>

      {/* Active students: Unified floating cards */}
      {active.length === 0 ? (
        <motion.div 
          initial={{ opacity: 0, y: 10 }} 
          animate={{ opacity: 1, y: 0 }}
          className="bg-surface border-4 border-dashed border-primary/10 rounded-[32px] p-8 sm:p-12 text-center text-foreground/50 max-w-2xl mx-auto my-12"
        >
          <div className="w-20 h-20 bg-secondary/20 text-secondary rounded-full flex items-center justify-center mx-auto mb-6">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><line x1="19" x2="19" y1="8" y2="14" /><line x1="22" x2="16" y1="11" y2="11" /></svg>
          </div>
          <h2 className="font-display text-3xl font-extrabold text-primary mb-3">No students yet</h2>
          <p className="text-foreground/70 text-lg mb-8 max-w-[35ch] mx-auto">
            Your classroom is ready. Add some students so they can start writing their first books!
          </p>
          <motion.button
            whileTap={{ y: 4, boxShadow: "0 0px 0 var(--color-primary-deep)" }}
            onClick={() => router.push(`/classroom/${classroomId}/add`)}
            className="min-h-[56px] px-8 rounded-2xl bg-primary text-on-primary text-lg font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-colors inline-flex items-center justify-center focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
          >
            + Add your first students
          </motion.button>
        </motion.div>
      ) : (
        <div className="space-y-3">
          {active.map((s, i) => (
            <motion.div
              key={s.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              whileHover={{ y: -2 }}
              style={{ zIndex: openMenuId === s.id ? 30 : active.length - i }}
              className={`bg-surface border-2 border-primary/5 rounded-2xl p-4 sm:px-6 flex items-center justify-between gap-4 hover:shadow-[0_8px_24px_rgba(49,85,217,0.08)] transition-all group relative ${
                openMenuId === s.id ? "z-30" : ""
              }`}
            >
              <div className="flex items-center gap-4 sm:gap-6">
                <Avatar avatarId={s.avatar_id} displayNickname={s.display_nickname} size={48} />
                <div>
                  <p className="font-bold text-foreground text-lg">{s.display_nickname}</p>
                  <div className="flex items-center mt-1">
                    <span className="text-sm font-mono text-foreground/50 bg-background px-2 py-0.5 rounded-lg border border-primary/5">@{s.nickname}</span>
                  </div>
                </div>
              </div>
              <RowMenu
                open={openMenuId === s.id}
                onToggle={() => setOpenMenuId((cur) => (cur === s.id ? null : s.id))}
                onClose={() => setOpenMenuId(null)}
                onReset={() => handleReset(s)}
                onRemove={() => setRemoving(s)}
              />
            </motion.div>
          ))}
        </div>
      )}

      {/* Removed students (collapsible) */}
      {removed.length > 0 && (
        <details className="mt-12 group">
          <summary className="cursor-pointer text-sm font-bold text-foreground/50 hover:text-primary transition-colors list-none flex items-center gap-2 select-none outline-none focus-visible:ring-[3px] focus-visible:ring-secondary rounded-lg inline-flex pr-2">
            <span className="transition-transform group-open:rotate-90">▸</span> 
            Show removed students ({removed.length})
          </summary>
          <div className="mt-4 space-y-2 pl-4 border-l-4 border-primary/10">
            {removed.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between px-4 py-3 bg-surface/50 rounded-xl text-sm text-foreground/60 hover:bg-surface transition-colors"
              >
                <span className="font-bold text-foreground/80 text-base">{s.display_nickname}</span>
                <button
                  onClick={() => handleAddBack(s)}
                  className="text-primary text-xs font-bold hover:underline min-h-[36px] px-4 bg-primary/5 hover:bg-primary/10 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
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
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="bg-surface rounded-[32px] p-8 max-w-sm w-full border-2 border-primary/10 shadow-[0_22px_60px_rgba(49,85,217,0.16)] text-center"
          >
            <div className="w-16 h-16 bg-primary/10 text-primary rounded-full flex items-center justify-center mx-auto mb-4">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>
            </div>
            <h2 className="font-display text-2xl font-extrabold mb-2 text-primary">Word reset</h2>
            <p className="text-sm text-foreground/70 mb-6">
              Give this to <span className="font-bold text-foreground">{slip.display_nickname}</span>. It won&apos;t be shown again.
            </p>
            <div className="bg-background rounded-2xl p-6 mb-6 border-2 border-primary/5">
              <p className="text-xs font-bold text-foreground/50 uppercase tracking-wider mb-1">Class code</p>
              <p className="font-mono font-bold text-lg mb-4">{classroom.code}</p>
              
              <p className="text-xs font-bold text-foreground/50 uppercase tracking-wider mb-1">Nickname</p>
              <p className="font-mono font-bold text-lg mb-4">{slip.nickname}</p>
              
              <p className="text-xs font-bold text-foreground/50 uppercase tracking-wider mb-1">New Word</p>
              <p className="font-mono font-bold text-3xl text-primary">{slip.password}</p>
            </div>
            <motion.button
              whileTap={{ scale: 0.96 }}
              onClick={() => setSlip(null)}
              className="w-full min-h-[56px] bg-muted hover:bg-muted/80 rounded-2xl font-extrabold text-lg transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
            >
              Done
            </motion.button>
          </motion.div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          role="status"
          className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-foreground text-background px-6 py-4 rounded-2xl text-sm font-bold shadow-[0_10px_28px_rgba(0,0,0,0.2)] z-50 flex items-center gap-3"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="text-background/80"><polyline points="20 6 9 17 4 12"></polyline></svg>
          {toast}
        </motion.div>
      )}
    </div>
  );
}

function RowMenu({
  open,
  onToggle,
  onClose,
  onReset,
  onRemove,
}: {
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
  onReset: () => void;
  onRemove: () => void;
}) {
  return (
    <div className={`relative inline-block shrink-0 ${open ? "z-30" : ""}`}>
      {/* ponytail: plain conditional render + backdrop. The popover API put this in the
          top layer, where `position: absolute` resolves against the viewport, not the
          button — `top: 100%` painted the menu below the fold. */}
      <motion.button
        whileTap={{ scale: 0.95 }}
        onClick={onToggle}
        aria-expanded={open}
        aria-haspopup="menu"
        className="w-12 h-12 flex items-center justify-center rounded-xl hover:bg-primary/5 transition-colors text-foreground/60 font-bold focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
        aria-label="Student actions"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/><circle cx="5" cy="12" r="1.5"/></svg>
      </motion.button>
      {open && (
        <>
          <button
            aria-hidden
            tabIndex={-1}
            onClick={onClose}
            className="fixed inset-0 z-10 cursor-default"
          />
          <div
            role="menu"
            className="absolute right-0 top-full mt-2 bg-surface border-2 border-primary/10 rounded-2xl shadow-[0_10px_28px_rgba(49,85,217,0.12)] p-2 min-w-[160px] z-20"
          >
            <button
              role="menuitem"
              onClick={() => {
                onClose();
                onReset();
              }}
              className="w-full text-left px-4 py-3 text-sm rounded-xl hover:bg-muted transition-colors font-bold focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
            >
              Reset word
            </button>
            <button
              role="menuitem"
              onClick={() => {
                onClose();
                onRemove();
              }}
              className="w-full text-left px-4 py-3 text-sm rounded-xl hover:bg-destructive/10 transition-colors font-bold text-destructive focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
            >
              Remove
            </button>
          </div>
        </>
      )}
    </div>
  );
}
