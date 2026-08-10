import Link from "next/link";

export default function TermsOfService() {
  return (
    <div className="min-h-[100dvh] bg-background text-foreground relative py-12 px-6 sm:px-12">
      <div className="absolute top-6 left-6 sm:top-8 sm:left-8 z-50">
        <Link href="/" className="inline-flex items-center gap-2 text-primary hover:text-primary-deep font-bold text-sm transition-colors group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary rounded-lg px-2 py-1 -ml-2">
          <svg className="w-4 h-4 transition-transform group-hover:-translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          Home
        </Link>
      </div>

      <div className="max-w-3xl mx-auto mt-12 bg-surface rounded-3xl p-8 sm:p-12 shadow-sm border border-primary/10">
        <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-primary mb-6">Terms of Service</h1>
        <p className="text-foreground/70 mb-10 text-lg">Last updated: August 2026</p>

        <div className="space-y-10 text-foreground/80 leading-relaxed">
          <section>
            <h2 className="font-display text-2xl font-bold text-primary mb-4">1. Who Can Use Story Buddy</h2>
            <ul className="list-disc pl-5 space-y-3">
              <li><strong>Educators:</strong> Only teachers or education students can create a classroom account.</li>
              <li><strong>Students:</strong> Students in Grades 5 and 6 may use the platform only through accounts issued by their teacher. Teachers are responsible for obtaining guardian consent before adding a student to the classroom.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-2xl font-bold text-primary mb-4">2. Teacher Responsibilities</h2>
            <ul className="list-disc pl-5 space-y-3">
              <li><strong>The Gatekeeper Role:</strong> Teachers must manually review and approve every completed storybook. A book cannot enter the classroom gallery or be exported as a PDF until the teacher says it is okay.</li>
              <li><strong>Account Management:</strong> Teachers manage student nicknames and passwords and are responsible for deleting student accounts upon guardian request.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-2xl font-bold text-primary mb-4">3. Platform Rules and Limits</h2>
            <ul className="list-disc pl-5 space-y-3">
              <li><strong>Safe Environment:</strong> Story Buddy is a safe space. Our automated moderation tools will block unsafe text and images.</li>
              <li><strong>No Social Networking:</strong> The platform is a closed gallery. Students can read approved books in their classroom, but there are no comments, likes, or public sharing features.</li>
              <li><strong>Usage Limits:</strong> To ensure fair use and prevent abuse, classrooms and student accounts have a daily limit on how many storybook generations they can run.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-2xl font-bold text-primary mb-4">4. Ownership and Export</h2>
            <p>Students own their original stories. Once a storybook is approved, it can be downloaded as a PDF so the child can share their specific story with family, rather than sharing access to the platform itself.</p>
          </section>
        </div>
      </div>
    </div>
  );
}
