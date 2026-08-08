"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Plus, Users, BookOpen, Gear, X, Warning, Key, Trash, UserCircle, Door } from "@phosphor-icons/react";

// Types
type Student = {
  id: number;
  nickname: string;
  display_nickname: string;
  password?: string;
  status: "active" | "removed";
};

// Initial state
const INITIAL_STUDENTS: Student[] = [
  { id: 1, nickname: "Alex", display_nickname: "Alex M.", status: "active" },
  { id: 2, nickname: "Alex (1)", display_nickname: "Alex T.", status: "active" },
  { id: 3, nickname: "Sam", display_nickname: "Sammy", status: "removed" },
];

export default function PrototypePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const variant = searchParams.get("variant") || "A";

  const [students, setStudents] = useState<Student[]>(INITIAL_STUDENTS);
  const [newStudentName, setNewStudentName] = useState("");
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  // Switch variant
  const setVariant = (v: string) => {
    router.push(`?variant=${v}`);
  };

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStudentName.trim()) return;
    
    // Simulate nickname derivation & collision
    const baseNick = newStudentName.split(" ")[0];
    let nick = baseNick;
    let counter = 1;
    while (students.some((s) => s.nickname === nick)) {
      nick = `${baseNick} (${counter})`;
      counter++;
    }

    const newStudent: Student = {
      id: Date.now(),
      nickname: nick,
      display_nickname: newStudentName,
      status: "active",
      password: "new-secret-word"
    };

    setStudents([...students, newStudent]);
    setGeneratedPassword(newStudent.password!);
    setNewStudentName("");
    // We don't close the modal immediately so they can see the password
  };

  const handleRemove = (id: number) => {
    setStudents(students.map(s => s.id === id ? { ...s, status: "removed" } : s));
  };

  const activeStudents = students.filter(s => s.status === "active");

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)] font-[var(--font-kid)] pb-24">
      {/* Prototype specific header */}
      <div className="bg-[var(--color-admin)] text-[var(--on-admin)] p-2 text-center text-sm font-[var(--font-sans)] font-medium flex justify-center items-center gap-4">
        <span>PROTOTYPE: S2 Teacher Shell & Provisioning</span>
        <button onClick={() => setStudents(INITIAL_STUDENTS)} className="underline opacity-80 hover:opacity-100">Reset State</button>
      </div>

      <div className="flex h-[calc(100vh-40px)]">
        {/* Shell Sidebar */}
        <aside className="w-64 bg-[var(--color-surface)] border-r border-[color-mix(in_srgb,var(--color-primary)_15%,transparent)] p-6 flex flex-col justify-between">
          <div>
            <div className="font-[var(--font-display)] text-2xl text-[var(--color-primary)] font-bold mb-8">StoryBuddy</div>
            <div className="space-y-2">
              <div className="px-4 py-2 bg-[var(--color-muted)] rounded-xl text-sm mb-4 font-bold text-center">
                <span className="opacity-70 block text-xs">Class Code</span>
                <span className="font-[var(--font-mono)] tracking-wider">X4J9K</span>
              </div>
              <button className="flex items-center gap-3 px-4 py-3 rounded-xl w-full text-left bg-[var(--color-primary)] text-[var(--on-primary)] font-bold shadow-sm">
                <Users size={20} weight="bold" /> Roster
              </button>
              <button className="flex items-center gap-3 px-4 py-3 rounded-xl w-full text-left hover:bg-[var(--color-muted)] text-[var(--color-primary-deep)] font-medium transition-colors">
                <BookOpen size={20} weight="bold" /> Books
              </button>
            </div>
          </div>
          <div className="space-y-2">
            <button className="flex items-center gap-3 px-4 py-3 rounded-xl w-full text-left hover:bg-[var(--color-muted)] text-[var(--color-primary-deep)] font-medium transition-colors">
              <Gear size={20} weight="bold" /> Settings
            </button>
            <button className="flex items-center gap-3 px-4 py-3 rounded-xl w-full text-left hover:bg-[var(--color-muted)] text-[var(--color-primary-deep)] font-medium transition-colors">
              <Door size={20} weight="bold" /> Log Out
            </button>
          </div>
        </aside>

        {/* Main Content Area based on Variant */}
        <main className="flex-1 overflow-auto p-8 md:p-12">
          <div className="max-w-6xl mx-auto h-full">
            {variant === "A" && <VariantA activeStudents={activeStudents} showAddModal={showAddModal} setShowAddModal={setShowAddModal} handleAdd={handleAdd} newStudentName={newStudentName} setNewStudentName={setNewStudentName} generatedPassword={generatedPassword} setGeneratedPassword={setGeneratedPassword} handleRemove={handleRemove} />}
            {variant === "B" && <VariantB activeStudents={activeStudents} handleAdd={handleAdd} newStudentName={newStudentName} setNewStudentName={setNewStudentName} generatedPassword={generatedPassword} setGeneratedPassword={setGeneratedPassword} handleRemove={handleRemove} />}
            {variant === "C" && <VariantC activeStudents={activeStudents} handleAdd={handleAdd} newStudentName={newStudentName} setNewStudentName={setNewStudentName} generatedPassword={generatedPassword} setGeneratedPassword={setGeneratedPassword} handleRemove={handleRemove} />}
          </div>
        </main>
      </div>

      {/* Floating Bottom Bar for Variant Switching */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-[var(--color-surface)] neo-shadow-xl rounded-full px-6 py-4 flex items-center gap-4 z-[var(--z-toast)] border border-[color-mix(in_srgb,var(--color-primary)_15%,transparent)]">
        <span className="font-[var(--font-sans)] text-sm font-bold opacity-60 uppercase tracking-wider">UI Variant:</span>
        <button onClick={() => setVariant("A")} className={`px-4 py-2 rounded-xl font-bold transition-colors ${variant === "A" ? "bg-[var(--color-primary)] text-[var(--on-primary)]" : "hover:bg-[var(--color-muted)]"}`}>A: Cards & Modals</button>
        <button onClick={() => setVariant("B")} className={`px-4 py-2 rounded-xl font-bold transition-colors ${variant === "B" ? "bg-[var(--color-primary)] text-[var(--on-primary)]" : "hover:bg-[var(--color-muted)]"}`}>B: Dense Admin</button>
        <button onClick={() => setVariant("C")} className={`px-4 py-2 rounded-xl font-bold transition-colors ${variant === "C" ? "bg-[var(--color-primary)] text-[var(--on-primary)]" : "hover:bg-[var(--color-muted)]"}`}>C: Split View</button>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// VARIANT A: Cards & Modals (Cobalt Heavy, child-adjacent design)
// ----------------------------------------------------------------------------
function VariantA({ activeStudents, showAddModal, setShowAddModal, handleAdd, newStudentName, setNewStudentName, generatedPassword, setGeneratedPassword, handleRemove }: any) {
  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-4xl font-[var(--font-display)] font-bold text-[var(--foreground)] tracking-tight">Roster</h1>
          <p className="text-lg opacity-80 mt-2">Manage your students and their logins.</p>
        </div>
        <button onClick={() => { setShowAddModal(true); setGeneratedPassword(null); }} className="bg-[var(--color-primary)] text-[var(--on-primary)] px-6 py-3 rounded-2xl font-bold flex items-center gap-2 neo-shadow-sm hover:-translate-y-0.5 transition-transform">
          <Plus weight="bold" /> Add Student
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {activeStudents.map((s: any) => (
          <div key={s.id} className="bg-[var(--color-surface)] p-6 rounded-3xl neo-shadow-sm border border-[color-mix(in_srgb,var(--color-primary)_10%,transparent)] relative group flex flex-col h-full">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-[var(--color-muted)] flex items-center justify-center text-[var(--color-primary)] font-bold text-xl shrink-0">
                  {s.display_nickname.charAt(0)}
                </div>
                <div>
                  <h3 className="font-bold text-xl leading-tight">{s.display_nickname}</h3>
                  <div className="text-sm opacity-70 flex items-center gap-1 mt-1">
                    <UserCircle size={16} /> @{s.nickname}
                  </div>
                </div>
              </div>
            </div>
            
            {s.display_nickname !== s.nickname && (
              <div className="mb-4 text-xs bg-[var(--color-warning)]/10 text-[var(--color-warning)] px-3 py-2 rounded-lg flex items-center gap-2 font-bold leading-tight">
                <Warning size={16} weight="fill" className="shrink-0" /> Nickname resolved to "{s.nickname}"
              </div>
            )}

            <div className="mt-auto pt-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button className="flex-1 bg-[var(--background)] px-4 py-2 rounded-xl text-sm font-bold flex justify-center items-center gap-2 hover:bg-[var(--color-muted)] transition-colors">
                <Key weight="bold" /> Reset PIN
              </button>
              <button onClick={() => handleRemove(s.id)} className="bg-[var(--background)] px-4 py-2 rounded-xl text-[var(--color-destructive)] hover:bg-[var(--color-destructive)]/10 transition-colors" aria-label="Remove student">
                <Trash weight="bold" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {showAddModal && (
        <div className="fixed inset-0 bg-[#18204A]/40 backdrop-blur-sm z-[var(--z-modal)] flex items-center justify-center p-4">
          <div className="bg-[var(--color-surface)] rounded-3xl p-8 max-w-md w-full neo-shadow-xl border border-[color-mix(in_srgb,var(--color-primary)_20%,transparent)]">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-[var(--font-display)] font-bold">Add Student</h2>
              <button onClick={() => setShowAddModal(false)} className="p-2 bg-[var(--background)] rounded-full hover:bg-[var(--color-muted)]"><X weight="bold" /></button>
            </div>

            {!generatedPassword ? (
              <form onSubmit={handleAdd} className="space-y-6">
                <div>
                  <label className="block font-bold mb-2">Student Name (e.g., First name + Last initial)</label>
                  <input autoFocus type="text" value={newStudentName} onChange={e => setNewStudentName(e.target.value)} className="w-full bg-[var(--background)] border-2 border-[var(--color-muted)] rounded-2xl px-4 py-3 focus:border-[var(--color-secondary)] focus:outline-none transition-colors" placeholder="Alex M." />
                </div>
                <button type="submit" disabled={!newStudentName.trim()} className="w-full bg-[var(--color-primary)] text-[var(--on-primary)] py-4 rounded-2xl font-bold disabled:opacity-50 disabled:cursor-not-allowed text-lg neo-shadow-sm">
                  Create Student
                </button>
              </form>
            ) : (
              <div className="space-y-6 text-center animate-in zoom-in-95 duration-200">
                <div className="w-16 h-16 bg-[var(--color-success)]/10 text-[var(--color-success)] rounded-full flex items-center justify-center mx-auto">
                  <Key size={32} weight="fill" />
                </div>
                <div>
                  <h3 className="font-bold text-xl mb-2">Student Created!</h3>
                  <p className="opacity-80">Give this one-time password to the student. They will use it to log in.</p>
                </div>
                <div className="bg-[var(--background)] border-2 border-[var(--color-primary)]/20 p-6 rounded-2xl">
                  <div className="font-[var(--font-mono)] text-2xl font-bold text-[var(--color-primary-deep)] tracking-widest">{generatedPassword}</div>
                </div>
                <button onClick={() => { setShowAddModal(false); setGeneratedPassword(null); }} className="w-full bg-[var(--color-muted)] text-[var(--foreground)] py-4 rounded-2xl font-bold">
                  Done
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------------
// VARIANT B: Dense Admin (Inter font, inline addition)
// ----------------------------------------------------------------------------
function VariantB({ activeStudents, handleAdd, newStudentName, setNewStudentName, generatedPassword, setGeneratedPassword, handleRemove }: any) {
  return (
    <div className="space-y-8 animate-in fade-in duration-300 font-[var(--font-sans)]">
      <div className="flex justify-between items-end border-b border-[var(--color-muted)] pb-6">
        <div>
          <h1 className="text-3xl font-[var(--font-display)] font-bold text-[var(--foreground)]">Roster Management</h1>
          <p className="text-sm opacity-70 mt-1">Manage active students and provisioning.</p>
        </div>
      </div>

      <div className="bg-[var(--color-surface)] border border-[var(--color-muted)] rounded-2xl overflow-hidden neo-shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--background)] border-b border-[var(--color-muted)] font-bold text-[var(--color-primary-deep)] uppercase tracking-wider text-xs">
            <tr>
              <th className="px-6 py-4">Display Name</th>
              <th className="px-6 py-4">Derived Nickname (@)</th>
              <th className="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-muted)]">
            {activeStudents.map((s: any) => (
              <tr key={s.id} className="hover:bg-[var(--background)]/50 transition-colors">
                <td className="px-6 py-4 font-medium text-base">{s.display_nickname}</td>
                <td className="px-6 py-4">
                  <span className="font-[var(--font-mono)] bg-[var(--color-muted)]/50 px-2 py-1 rounded text-xs">
                    {s.nickname}
                  </span>
                  {s.display_nickname !== s.nickname && (
                    <span className="ml-2 text-[var(--color-warning)] text-xs font-bold" title="Collision prevented">⚠ Resolved</span>
                  )}
                </td>
                <td className="px-6 py-4 text-right space-x-4">
                  <button className="text-[var(--color-primary)] font-bold hover:underline">Reset PIN</button>
                  <button onClick={() => handleRemove(s.id)} className="text-[var(--color-destructive)] font-bold hover:underline">Remove</button>
                </td>
              </tr>
            ))}
            
            {/* Inline Add Row */}
            <tr className="bg-[var(--color-primary)]/5">
              <td colSpan={3} className="px-6 py-4">
                {!generatedPassword ? (
                  <form onSubmit={handleAdd} className="flex gap-4 items-center">
                    <input 
                      type="text" 
                      value={newStudentName} 
                      onChange={e => setNewStudentName(e.target.value)} 
                      className="bg-[var(--color-surface)] border border-[var(--color-primary)]/30 rounded-xl px-4 py-2 focus:border-[var(--color-primary)] focus:outline-none flex-1 max-w-sm" 
                      placeholder="Add new student (e.g. Alex M.)" 
                    />
                    <button type="submit" disabled={!newStudentName.trim()} className="bg-[var(--color-primary)] text-[var(--on-primary)] px-4 py-2 rounded-xl font-bold disabled:opacity-50 text-sm neo-shadow-xs">
                      Create
                    </button>
                  </form>
                ) : (
                  <div className="flex items-center gap-4 bg-[var(--color-success)]/10 text-[var(--color-success)] p-3 rounded-xl border border-[var(--color-success)]/20">
                    <Key weight="fill" />
                    <span className="font-bold text-sm">Student created! One-time password: </span>
                    <span className="font-[var(--font-mono)] bg-[var(--color-surface)] px-3 py-1 rounded font-bold border border-[var(--color-success)]/20">{generatedPassword}</span>
                    <button onClick={() => setGeneratedPassword(null)} className="ml-auto text-xs font-bold underline">Dismiss</button>
                  </div>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// VARIANT C: Split View (List on left, details/actions on right)
// ----------------------------------------------------------------------------
function VariantC({ activeStudents, handleAdd, newStudentName, setNewStudentName, generatedPassword, setGeneratedPassword, handleRemove }: any) {
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null);
  const selectedStudent = activeStudents.find((s: any) => s.id === selectedStudentId);

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      <h1 className="text-3xl font-[var(--font-display)] font-bold text-[var(--foreground)] mb-6">Student Roster</h1>
      
      <div className="flex-1 flex gap-8 overflow-hidden">
        {/* Left List */}
        <div className="w-1/3 flex flex-col bg-[var(--color-surface)] border border-[var(--color-muted)] rounded-3xl overflow-hidden neo-shadow-sm shrink-0">
          <div className="p-4 border-b border-[var(--color-muted)] bg-[var(--background)]">
            <h2 className="font-bold text-lg text-[var(--color-primary-deep)]">Class List</h2>
          </div>
          <div className="flex-1 overflow-auto p-2 space-y-1">
            {activeStudents.map((s: any) => (
              <button 
                key={s.id} 
                onClick={() => setSelectedStudentId(s.id)}
                className={`w-full text-left px-4 py-3 rounded-2xl flex items-center justify-between transition-colors ${selectedStudentId === s.id ? 'bg-[var(--color-primary)] text-[var(--on-primary)]' : 'hover:bg-[var(--background)]'}`}
              >
                <div className="font-bold">{s.display_nickname}</div>
                {s.display_nickname !== s.nickname && <Warning size={16} weight={selectedStudentId === s.id ? "regular" : "fill"} className={selectedStudentId === s.id ? "text-[var(--on-primary)]" : "text-[var(--color-warning)]"} />}
              </button>
            ))}
          </div>
          <div className="p-4 border-t border-[var(--color-muted)] bg-[var(--background)]">
            <button onClick={() => setSelectedStudentId(-1)} className={`w-full py-3 rounded-2xl font-bold flex justify-center items-center gap-2 border-2 ${selectedStudentId === -1 ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10 text-[var(--color-primary-deep)]' : 'border-[var(--color-muted)] hover:border-[var(--color-primary)]/50 text-[var(--color-primary)]'} transition-colors`}>
              <Plus weight="bold" /> New Student
            </button>
          </div>
        </div>

        {/* Right Detail Pane */}
        <div className="flex-1 bg-[var(--color-surface)] border border-[var(--color-muted)] rounded-3xl p-10 overflow-auto neo-shadow-sm">
          {!selectedStudentId ? (
            <div className="h-full flex flex-col items-center justify-center text-center opacity-50">
              <Users size={64} weight="thin" className="mb-4" />
              <p className="font-bold text-lg">Select a student</p>
              <p className="text-sm">View details, reset PIN, or remove.</p>
            </div>
          ) : selectedStudentId === -1 ? (
            <div className="animate-in slide-in-from-right-4 duration-300 max-w-md">
              <h2 className="text-3xl font-[var(--font-display)] font-bold mb-6">Add New Student</h2>
              {!generatedPassword ? (
                <form onSubmit={(e) => { handleAdd(e); /* Keep selected to show password */ }} className="space-y-6">
                  <div>
                    <label className="block font-bold mb-2">Display Name</label>
                    <input autoFocus type="text" value={newStudentName} onChange={e => setNewStudentName(e.target.value)} className="w-full bg-[var(--background)] border-2 border-[var(--color-muted)] rounded-2xl px-4 py-3 focus:border-[var(--color-secondary)] focus:outline-none transition-colors" placeholder="e.g. Alex M." />
                    <p className="text-sm opacity-70 mt-2">Nickname will be auto-generated to ensure uniqueness.</p>
                  </div>
                  <button type="submit" disabled={!newStudentName.trim()} className="w-full bg-[var(--color-primary)] text-[var(--on-primary)] py-4 rounded-2xl font-bold neo-shadow-sm">
                    Create Student
                  </button>
                </form>
              ) : (
                <div className="bg-[var(--color-success)]/10 text-[var(--color-success)] p-8 rounded-3xl text-center border border-[var(--color-success)]/20">
                  <Key size={48} weight="fill" className="mx-auto mb-4" />
                  <h3 className="font-bold text-2xl mb-2">Student Created!</h3>
                  <p className="text-base opacity-80 mb-6 text-[var(--foreground)]">Share this one-time PIN:</p>
                  <div className="font-[var(--font-mono)] text-3xl font-bold bg-[var(--color-surface)] py-4 rounded-2xl border border-[var(--color-success)]/20 mb-8 text-[var(--color-primary-deep)]">{generatedPassword}</div>
                  <button onClick={() => { setGeneratedPassword(null); setSelectedStudentId(null); }} className="font-bold text-lg underline hover:text-[var(--color-primary)]">Dismiss</button>
                </div>
              )}
            </div>
          ) : (
             <div className="animate-in slide-in-from-right-4 duration-300 max-w-lg">
                <div className="w-24 h-24 rounded-full bg-[var(--color-muted)] flex items-center justify-center text-[var(--color-primary)] font-bold text-4xl mb-6">
                  {selectedStudent?.display_nickname.charAt(0)}
                </div>
                <h2 className="text-4xl font-[var(--font-display)] font-bold mb-2">{selectedStudent?.display_nickname}</h2>
                <div className="inline-block bg-[var(--background)] border border-[var(--color-muted)] px-3 py-1 rounded-lg text-sm font-bold opacity-70 mb-8">
                  @{selectedStudent?.nickname}
                </div>
                
                {selectedStudent?.display_nickname !== selectedStudent?.nickname && (
                  <div className="mb-8 p-4 bg-[var(--color-warning)]/10 text-[var(--color-warning)] rounded-2xl flex gap-3 text-sm font-bold">
                    <Warning size={20} weight="fill" className="shrink-0" />
                    <div>Nickname was changed from "{selectedStudent?.display_nickname.split(' ')[0]}" to prevent a collision with another student.</div>
                  </div>
                )}

                <div className="space-y-4 pt-8 border-t border-[var(--color-muted)]">
                  <h3 className="font-bold text-lg mb-4 font-[var(--font-display)]">Actions</h3>
                  <button className="w-full py-4 bg-[var(--background)] border-2 border-[var(--color-primary)] text-[var(--color-primary)] rounded-2xl font-bold flex items-center justify-center gap-2 hover:bg-[var(--color-primary)]/5 transition-colors">
                    <Key weight="bold" /> Generate New PIN
                  </button>
                  <button onClick={() => { handleRemove(selectedStudent!.id); setSelectedStudentId(null); }} className="w-full py-4 bg-[var(--color-destructive)]/10 text-[var(--color-destructive)] rounded-2xl font-bold flex items-center justify-center gap-2 hover:bg-[var(--color-destructive)]/20 transition-colors">
                    <Trash weight="bold" /> Remove from Roster
                  </button>
                </div>
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
