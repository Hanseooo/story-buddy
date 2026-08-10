import Link from "next/link";

export default function PrivacyPolicy() {
  return (
    <div className="min-h-[100dvh] bg-background text-foreground relative py-12 px-6 sm:px-12">
      <div className="absolute top-6 left-6 sm:top-8 sm:left-8 z-50">
        <Link href="/" className="inline-flex items-center gap-2 text-primary hover:text-primary-deep font-bold text-sm transition-colors group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary rounded-lg px-2 py-1 -ml-2">
          <svg className="w-4 h-4 transition-transform group-hover:-translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          Home
        </Link>
      </div>

      <div className="max-w-3xl mx-auto mt-12 bg-surface rounded-3xl p-8 sm:p-12 shadow-sm border border-primary/10">
        <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-primary mb-6">Privacy Policy</h1>
        <p className="text-foreground/70 mb-10 text-lg">Last updated: August 2026</p>

        <div className="space-y-10 text-foreground/80 leading-relaxed">
          <section>
            <h2 className="font-display text-2xl font-bold text-primary mb-4">1. What Information We Collect</h2>
            <ul className="list-disc pl-5 space-y-3">
              <li><strong>From Teachers:</strong> Account information like email and password to manage the classroom.</li>
              <li><strong>From Students:</strong> We practice minimal data collection. Students only use a nickname and a teacher-provided password. We do not collect student emails or allow self-serve signups.</li>
              <li><strong>Student Stories:</strong> The original text stories written by the students.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-2xl font-bold text-primary mb-4">2. How We Protect and Process Data</h2>
            <ul className="list-disc pl-5 space-y-3">
              <li><strong>Strict Privacy by Design:</strong> A child narrating their real life is expected. We automatically scrub personal identifiable information (PII) like names and Filipino addresses from the text before any story is saved, narrated, or exported.</li>
              <li><strong>Classroom Isolation:</strong> Student data is locked to their specific classroom and account using strict database rules. Only the student and their teacher can see their work. There is absolutely no public sharing mode.</li>
              <li><strong>AI Processing:</strong> To turn stories into picture books, the redacted text is processed securely by our AI partners (OpenRouter, fal.ai) to generate images and narration (via Chatterbox). All infrastructure is hosted securely in the Singapore region.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-display text-2xl font-bold text-primary mb-4">3. Content Moderation</h2>
            <p className="mb-3">Every story and generated image passes through multiple open-weight safety filters before it reaches the child.</p>
            <p>If a scene fails safety checks, the system will gently ask the student to rewrite it.</p>
          </section>

          <section>
            <h2 className="font-display text-2xl font-bold text-primary mb-4">4. Data Deletion and Guardian Rights</h2>
            <p>Parents and guardians are the ultimate consent givers. If a parent requests data removal, teachers have a one-action button to permanently delete a student&apos;s data and account from our systems.</p>
          </section>
        </div>
      </div>
    </div>
  );
}
