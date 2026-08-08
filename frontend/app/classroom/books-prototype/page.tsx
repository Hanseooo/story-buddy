"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Users, BookOpen, Gear, Door, CheckCircle, XCircle, Clock, X } from "@phosphor-icons/react";

// Types
export type Page = {
  scene_id: string;
  caption: string;
  image_url: string;
};

export type Job = {
  id: string;
  student_name: string;
  title: string;
  created_at: string;
  approved_at: string | null;
  rejected_at: string | null;
  pages: Page[];
  is_student_removed: boolean;
};

const SAMPLE_PAGES: Page[] = [
  { scene_id: "s1", caption: "Once upon a time, a brave dog went to the moon.", image_url: "https://placehold.co/600x400/3155D9/FFFDF7?text=Scene+1" },
  { scene_id: "s2", caption: "He found a lot of cheese there.", image_url: "https://placehold.co/600x400/F2C85F/18204A?text=Scene+2" },
  { scene_id: "s3", caption: "And he ate it all and became happy.", image_url: "https://placehold.co/600x400/EC6A51/FFFDF7?text=Scene+3" },
];

const INITIAL_JOBS: Job[] = [
  { id: "j1", student_name: "Alex M.", title: "The Space Dog", created_at: "10 mins ago", approved_at: null, rejected_at: null, pages: SAMPLE_PAGES, is_student_removed: false },
  { id: "j2", student_name: "Sammy", title: "My Robot Friend", created_at: "1 hour ago", approved_at: "2026-08-07T10:00:00Z", rejected_at: null, pages: SAMPLE_PAGES, is_student_removed: true },
  { id: "j3", student_name: "Alex T.", title: "The Magic Tree", created_at: "2 hours ago", approved_at: null, rejected_at: "2026-08-07T09:00:00Z", pages: SAMPLE_PAGES, is_student_removed: false },
  { id: "j4", student_name: "Jordan", title: "A Trip to Mars", created_at: "Yesterday", approved_at: null, rejected_at: null, pages: SAMPLE_PAGES, is_student_removed: false },
];

export default function BooksPrototypePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const variant = searchParams.get("variant") || "A";

  const [jobs, setJobs] = useState<Job[]>(INITIAL_JOBS);
  const [filter, setFilter] = useState<"all" | "pending" | "approved" | "rejected">("all");
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);

  // Derive status from dates
  const getStatus = (job: Job) => {
    if (job.approved_at) return "approved";
    if (job.rejected_at) return "rejected";
    return "pending";
  };

  const filteredJobs = jobs.filter(job => {
    if (filter === "all") return true;
    return getStatus(job) === filter;
  });

  const setVariant = (v: string) => {
    router.push(`?variant=${v}`);
  };

  const handleDecision = (jobId: string, decision: "approve" | "reject" | "pending") => {
    setJobs(jobs.map(job => {
      if (job.id !== jobId) return job;
      const now = new Date().toISOString();
      if (decision === "approve") {
        return { ...job, approved_at: now, rejected_at: null };
      }
      if (decision === "reject") {
        return { ...job, approved_at: null, rejected_at: now };
      }
      return { ...job, approved_at: null, rejected_at: null };
    }));
  };

  const selectedJob = jobs.find(j => j.id === selectedJobId);

  // Dialog management
  useEffect(() => {
    if (selectedJobId && dialogRef.current) {
      dialogRef.current.showModal();
    } else if (!selectedJobId && dialogRef.current) {
      dialogRef.current.close();
    }
  }, [selectedJobId]);

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)] pb-24 font-[var(--font-kid)]">
      {/* Header */}
      <div className="bg-[var(--color-admin)] text-[var(--on-admin)] p-2 text-center text-sm font-[var(--font-sans)] font-medium flex justify-center items-center gap-4">
        <span>PROTOTYPE: S3 Review & Approval</span>
        <button onClick={() => setJobs(INITIAL_JOBS)} className="underline opacity-80 hover:opacity-100">Reset State</button>
      </div>

      <div className="flex h-[calc(100vh-40px)]">
        {/* Sidebar */}
        <aside className="w-64 bg-[var(--color-surface)] border-r border-[color-mix(in_srgb,var(--color-primary)_15%,transparent)] p-6 flex flex-col justify-between hidden md:flex">
          <div>
            <div className="font-[var(--font-display)] text-2xl text-[var(--color-primary)] font-bold mb-8">StoryBuddy</div>
            <div className="space-y-2">
              <button className="flex items-center gap-3 px-4 py-3 rounded-xl w-full text-left hover:bg-[var(--color-muted)] text-[var(--color-primary-deep)] font-medium transition-colors">
                <Users size={20} weight="bold" /> Roster
              </button>
              <button className="flex items-center justify-between px-4 py-3 rounded-xl w-full text-left bg-[var(--color-primary)] text-[var(--on-primary)] font-bold shadow-sm">
                <div className="flex items-center gap-3">
                  <BookOpen size={20} weight="bold" /> Books
                </div>
                {jobs.filter(j => getStatus(j) === "pending").length > 0 && (
                  <span className="bg-[var(--color-secondary)] text-[var(--foreground)] text-xs px-2 py-0.5 rounded-full">
                    {jobs.filter(j => getStatus(j) === "pending").length}
                  </span>
                )}
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

        {/* Main Content */}
        <main className="flex-1 overflow-auto p-6 md:p-12 relative">
          <div className="max-w-6xl mx-auto h-full">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4">
              <div>
                <h1 className="text-4xl font-[var(--font-display)] font-bold tracking-tight">Class Library</h1>
                <p className="text-lg opacity-80 mt-2">Review and approve your students&apos; stories.</p>
              </div>
              
              {/* Filter */}
              <div className="flex bg-[var(--color-surface)] p-1 rounded-2xl border border-[color-mix(in_srgb,var(--color-primary)_10%,transparent)] neo-shadow-sm font-bold">
                <button onClick={() => setFilter("all")} className={`px-4 py-2 rounded-xl transition-colors ${filter === "all" ? "bg-[var(--color-muted)]" : "hover:bg-[var(--color-muted)]/50"}`}>All</button>
                <button onClick={() => setFilter("pending")} className={`px-4 py-2 rounded-xl transition-colors flex items-center gap-2 ${filter === "pending" ? "bg-[var(--color-info)]/10 text-[var(--color-info)]" : "hover:bg-[var(--color-muted)]/50"}`}>
                  <Clock weight="bold" /> Pending
                </button>
                <button onClick={() => setFilter("approved")} className={`px-4 py-2 rounded-xl transition-colors flex items-center gap-2 ${filter === "approved" ? "bg-[var(--color-success)]/10 text-[var(--color-success)]" : "hover:bg-[var(--color-muted)]/50"}`}>
                  <CheckCircle weight="bold" /> Approved
                </button>
                <button onClick={() => setFilter("rejected")} className={`px-4 py-2 rounded-xl transition-colors flex items-center gap-2 ${filter === "rejected" ? "bg-[var(--color-destructive)]/10 text-[var(--color-destructive)]" : "hover:bg-[var(--color-muted)]/50"}`}>
                  <XCircle weight="bold" /> Rejected
                </button>
              </div>
            </div>

            {variant === "A" && <VariantA jobs={filteredJobs} getStatus={getStatus} onOpen={setSelectedJobId} onDecision={handleDecision} />}
            {variant === "B" && <VariantB jobs={filteredJobs} getStatus={getStatus} onOpen={setSelectedJobId} onDecision={handleDecision} />}
          </div>
        </main>
      </div>

      {/* Reader Dialog (Shared) */}
      <dialog 
        ref={dialogRef}
        onCancel={(e) => { e.preventDefault(); setSelectedJobId(null); }}
        className="backdrop:bg-[#18204A]/60 backdrop:backdrop-blur-sm bg-transparent w-full h-full max-w-none max-h-none p-4 md:p-12 m-0 border-none flex items-center justify-center open:flex"
      >
        {selectedJob && (
          <div className="bg-[var(--color-surface)] w-full max-w-5xl rounded-[32px] flex flex-col h-full max-h-[90vh] neo-shadow-xl overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Dialog Header */}
            <div className="px-8 py-6 border-b border-[var(--color-muted)] flex justify-between items-center bg-[var(--background)] shrink-0">
              <div>
                <h2 className="text-2xl font-[var(--font-display)] font-bold">{selectedJob.title || "Untitled Story"}</h2>
                <p className="opacity-80">By {selectedJob.student_name} {selectedJob.is_student_removed && <span className="ml-2 text-xs font-bold bg-[var(--color-muted)] px-2 py-1 rounded">Removed Student</span>}</p>
              </div>
              <button 
                onClick={() => setSelectedJobId(null)}
                className="w-12 h-12 flex items-center justify-center bg-[var(--color-surface)] hover:bg-[var(--color-muted)] rounded-full transition-colors border border-[var(--color-muted)]"
              >
                <X size={24} weight="bold" />
              </button>
            </div>

            {/* Reader Body */}
            <div className="flex-1 overflow-auto bg-[var(--color-muted)]/30 p-8 flex flex-col items-center gap-12">
               {selectedJob.pages.map((page, i) => (
                 <div key={i} className="bg-[var(--color-surface)] max-w-3xl w-full rounded-2xl overflow-hidden neo-shadow-sm border border-[color-mix(in_srgb,var(--color-primary)_10%,transparent)]">
                    <img src={page.image_url} alt={`Scene ${i+1}`} className="w-full h-auto aspect-[3/2] object-cover" />
                    <div className="p-8 text-xl leading-relaxed font-[var(--font-kid)] text-center">
                      {page.caption}
                    </div>
                 </div>
               ))}
            </div>

            {/* Decision Footer */}
            <div className="px-8 py-6 border-t border-[var(--color-muted)] bg-[var(--color-surface)] shrink-0">
               <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                 <div className="flex items-center gap-4">
                   <div className="font-[var(--font-sans)] font-bold text-sm uppercase opacity-70 tracking-wider">Status:</div>
                   <StatusBadge status={getStatus(selectedJob)} />
                 </div>
                 
                 <div className="flex items-center gap-3 w-full md:w-auto">
                    {getStatus(selectedJob) !== "pending" && (
                      <button 
                        onClick={() => handleDecision(selectedJob.id, "pending")}
                        className="px-6 py-3 rounded-2xl font-bold bg-[var(--color-muted)] hover:bg-[color-mix(in_srgb,var(--color-muted)_80%,black)] transition-colors flex items-center gap-2"
                      >
                        <Clock weight="bold" /> Mark Pending
                      </button>
                    )}
                    
                    {getStatus(selectedJob) !== "rejected" && (
                      <button 
                        onClick={() => { handleDecision(selectedJob.id, "reject"); setSelectedJobId(null); }}
                        className="px-6 py-3 rounded-2xl font-bold bg-[var(--background)] border-2 border-[var(--color-destructive)] text-[var(--color-destructive)] hover:bg-[var(--color-destructive)]/10 transition-colors flex items-center gap-2 flex-1 md:flex-none justify-center"
                      >
                        <XCircle weight="bold" /> Reject
                      </button>
                    )}
                    
                    {getStatus(selectedJob) !== "approved" && (
                      <button 
                        onClick={() => { handleDecision(selectedJob.id, "approve"); setSelectedJobId(null); }}
                        className="px-8 py-3 rounded-2xl font-bold bg-[var(--color-primary)] text-[var(--on-primary)] neo-shadow-sm hover:-translate-y-0.5 transition-all flex items-center gap-2 flex-1 md:flex-none justify-center"
                      >
                        <CheckCircle weight="bold" /> Approve
                      </button>
                    )}
                 </div>
               </div>
            </div>
          </div>
        )}
      </dialog>

      {/* Floating Bottom Bar for Variant Switching */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-[var(--color-surface)] neo-shadow-xl rounded-full px-6 py-4 flex items-center gap-4 z-50 border border-[color-mix(in_srgb,var(--color-primary)_15%,transparent)]">
        <span className="font-[var(--font-sans)] text-sm font-bold opacity-60 uppercase tracking-wider">UI Variant:</span>
        <button onClick={() => setVariant("A")} className={`px-4 py-2 rounded-xl font-bold transition-colors ${variant === "A" ? "bg-[var(--color-primary)] text-[var(--on-primary)]" : "hover:bg-[var(--color-muted)]"}`}>A: Visual Grid</button>
        <button onClick={() => setVariant("B")} className={`px-4 py-2 rounded-xl font-bold transition-colors ${variant === "B" ? "bg-[var(--color-primary)] text-[var(--on-primary)]" : "hover:bg-[var(--color-muted)]"}`}>B: Dense List</button>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Components
// ----------------------------------------------------------------------------
function StatusBadge({ status }: { status: "pending" | "approved" | "rejected" }) {
  if (status === "approved") return <span className="bg-[var(--color-success)]/15 text-[var(--color-success)] px-3 py-1.5 rounded-lg font-bold text-sm flex items-center gap-1.5 w-fit"><CheckCircle weight="fill" /> Approved</span>;
  if (status === "rejected") return <span className="bg-[var(--color-destructive)]/15 text-[var(--color-destructive)] px-3 py-1.5 rounded-lg font-bold text-sm flex items-center gap-1.5 w-fit"><XCircle weight="fill" /> Rejected</span>;
  return <span className="bg-[var(--color-info)]/15 text-[var(--color-info)] px-3 py-1.5 rounded-lg font-bold text-sm flex items-center gap-1.5 w-fit"><Clock weight="fill" /> Pending</span>;
}

// ----------------------------------------------------------------------------
// VARIANT A: Visual Grid
// ----------------------------------------------------------------------------
function VariantA({ jobs, getStatus, onOpen, onDecision }: { jobs: Job[], getStatus: (j: Job) => string, onOpen: (id: string) => void, onDecision: (id: string, d: "approve" | "reject" | "pending") => void }) {
  if (jobs.length === 0) return <EmptyState />;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 pb-32 animate-in fade-in duration-300">
      {jobs.map((job: Job) => (
        <div key={job.id} className="bg-[var(--color-surface)] rounded-[24px] overflow-hidden neo-shadow-sm border border-[color-mix(in_srgb,var(--color-primary)_10%,transparent)] group flex flex-col hover:border-[var(--color-primary)]/50 transition-colors">
          <div className="aspect-[4/3] bg-[var(--color-muted)] relative cursor-pointer" onClick={() => onOpen(job.id)}>
             <img src={job.pages[0].image_url} alt="Cover" className="w-full h-full object-cover" />
             <div className="absolute top-4 right-4">
               <StatusBadge status={getStatus(job)} />
             </div>
             <div className="absolute inset-0 bg-[#18204A]/0 group-hover:bg-[#18204A]/20 transition-colors flex items-center justify-center">
               <div className="bg-[var(--color-surface)] text-[var(--color-primary)] px-4 py-2 rounded-xl font-bold neo-shadow-sm opacity-0 group-hover:opacity-100 transition-opacity translate-y-2 group-hover:translate-y-0">
                 Read Story
               </div>
             </div>
          </div>
          
          <div className="p-6 flex-1 flex flex-col">
            <h3 className="font-bold text-xl mb-1 line-clamp-1">{job.title || "Untitled"}</h3>
            <div className="text-sm opacity-70 flex justify-between items-center mb-4">
              <span className="flex items-center gap-1"><Users size={16} /> {job.student_name}</span>
              <span>{job.created_at}</span>
            </div>

            {/* Quick Actions */}
            <div className="mt-auto grid grid-cols-2 gap-2">
               {getStatus(job) === "pending" ? (
                 <>
                  <button onClick={() => onDecision(job.id, "reject")} className="py-2.5 bg-[var(--background)] text-[var(--color-destructive)] rounded-xl font-bold hover:bg-[var(--color-destructive)]/10 transition-colors flex items-center justify-center gap-1.5 text-sm">
                    <XCircle weight="bold" /> Reject
                  </button>
                  <button onClick={() => onDecision(job.id, "approve")} className="py-2.5 bg-[var(--color-primary)] text-[var(--on-primary)] rounded-xl font-bold neo-shadow-xs hover:-translate-y-0.5 transition-transform flex items-center justify-center gap-1.5 text-sm">
                    <CheckCircle weight="bold" /> Approve
                  </button>
                 </>
               ) : (
                 <button onClick={() => onDecision(job.id, "pending")} className="col-span-2 py-2.5 bg-[var(--background)] border border-[var(--color-muted)] rounded-xl font-bold hover:bg-[var(--color-muted)] transition-colors flex items-center justify-center gap-1.5 text-sm">
                   <Clock weight="bold" /> Mark Pending
                 </button>
               )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ----------------------------------------------------------------------------
// VARIANT B: Dense List (Inter font)
// ----------------------------------------------------------------------------
function VariantB({ jobs, getStatus, onOpen, onDecision }: { jobs: Job[], getStatus: (j: Job) => string, onOpen: (id: string) => void, onDecision: (id: string, d: "approve" | "reject" | "pending") => void }) {
  if (jobs.length === 0) return <EmptyState />;

  return (
    <div className="bg-[var(--color-surface)] rounded-[24px] border border-[var(--color-muted)] neo-shadow-sm overflow-hidden pb-32 animate-in fade-in duration-300 font-[var(--font-sans)]">
      <table className="w-full text-left text-sm">
        <thead className="bg-[var(--background)] border-b border-[var(--color-muted)] font-bold text-[var(--color-primary-deep)] uppercase tracking-wider text-xs">
          <tr>
            <th className="px-6 py-4">Story</th>
            <th className="px-6 py-4">Author</th>
            <th className="px-6 py-4">Time</th>
            <th className="px-6 py-4">Status</th>
            <th className="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-muted)]">
          {jobs.map((job: Job) => (
            <tr key={job.id} className="hover:bg-[var(--background)]/50 transition-colors group cursor-pointer" onClick={() => onOpen(job.id)}>
              <td className="px-6 py-4 font-medium flex items-center gap-4">
                 <div className="w-12 h-12 rounded-lg bg-[var(--color-muted)] overflow-hidden shrink-0 hidden sm:block">
                   <img src={job.pages[0].image_url} alt="" className="w-full h-full object-cover" />
                 </div>
                 {job.title || "Untitled"}
              </td>
              <td className="px-6 py-4 opacity-80">{job.student_name}</td>
              <td className="px-6 py-4 opacity-70 text-xs">{job.created_at}</td>
              <td className="px-6 py-4">
                <StatusBadge status={getStatus(job)} />
              </td>
              <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                 <div className="flex justify-end gap-2">
                   {getStatus(job) === "pending" ? (
                     <>
                      <button onClick={() => onDecision(job.id, "reject")} className="p-2 text-[var(--color-destructive)] hover:bg-[var(--color-destructive)]/10 rounded-lg transition-colors" title="Reject">
                        <XCircle size={20} weight="bold" />
                      </button>
                      <button onClick={() => onDecision(job.id, "approve")} className="p-2 text-[var(--color-success)] hover:bg-[var(--color-success)]/10 rounded-lg transition-colors" title="Approve">
                        <CheckCircle size={20} weight="bold" />
                      </button>
                     </>
                   ) : (
                     <button onClick={() => onDecision(job.id, "pending")} className="text-xs font-bold underline opacity-70 hover:opacity-100 px-2 py-2">
                       Undo
                     </button>
                   )}
                 </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 px-4 text-center opacity-70">
      <BookOpen size={64} weight="thin" className="mb-6 opacity-50" />
      <h3 className="text-2xl font-bold font-[var(--font-display)] mb-2">No books found</h3>
      <p>There are no stories matching this filter.</p>
    </div>
  );
}
