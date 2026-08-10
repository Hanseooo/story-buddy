import Link from "next/link";
import { ArrowLeft, ArrowRight } from "@phosphor-icons/react/dist/ssr";
import PipelineMap from "@/components/PipelineMap";
import WorkflowShowcase from "@/components/WorkflowShowcase";
import { FadeInStagger, FadeIn } from "@/components/FadeIn";
import { createSupabaseServerClient } from "@/utils/supabase/server";

export const metadata = {
  title: "StoryBuddy Methodology",
};

export default async function ResearchMethodologyPage() {
  const authClient = await createSupabaseServerClient();
  const { data: { user } } = await authClient.auth.getUser();
  let backHref = "/";
  let backLabel = "Back to Landing";

  if (user) {
    const { data: profile } = await authClient
      .from("profiles")
      .select("id, role")
      .eq("id", user.id)
      .single();

    if (profile?.role === "teacher") {
      backHref = "/classroom";
      backLabel = "Back to Classroom";
    } else if (profile?.id) {
      backHref = `/s/${profile.id}`;
      backLabel = "Back to Dashboard";
    }
  }

  return (
    <div className="min-h-[100dvh] bg-background text-foreground font-sans selection:bg-primary/20">
      {/* Navigation */}
      <nav className="border-b border-primary/10 bg-surface/80 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-4 flex items-center justify-between">
          <Link 
            href={backHref}
            className="inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:text-primary-deep transition-colors"
          >
            <ArrowLeft weight="bold" className="w-4 h-4" />
            {backLabel}
          </Link>
          
          <div className="flex items-center gap-2 select-none">
            <div className="grid size-7 place-items-center rounded-[9px_9px_9px_3px] overflow-hidden bg-surface shadow-sm shrink-0">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.png" alt="" className="h-full w-full object-contain scale-[1.35]" />
            </div>
            <span className="font-display text-lg font-extrabold text-primary tracking-tight hidden sm:block">
              StoryBuddy
            </span>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-10 py-16 md:py-24 space-y-32">
        
        {/* Hero Section */}
        <FadeInStagger className="flex flex-col gap-8 max-w-4xl">
          <FadeIn>
            <h1 className="text-5xl md:text-7xl lg:text-[88px] font-display font-extrabold tracking-tight text-foreground leading-[0.95]">
              Building a safe, consistent story pipeline.
            </h1>
          </FadeIn>
          <FadeIn>
            <p className="text-xl md:text-2xl text-foreground/80 leading-relaxed max-w-[55ch]">
              StoryBuddy is powered by a deterministic LangGraph architecture. We strictly use open-weight models and prioritize child safety, PII redaction, and narrative consistency above all else.
            </p>
          </FadeIn>
          <FadeIn>
            <div className="pt-4">
              <Link 
                href="/research/metrics" 
                className="inline-flex items-center gap-2 px-7 py-4 rounded-2xl bg-primary text-surface font-bold text-lg hover:bg-primary-deep transition-all shadow-[0_10px_28px_rgb(49_85_217/16%)] hover:shadow-[0_6px_18px_rgb(49_85_217/10%)] hover:translate-y-[2px]"
              >
                View Live Metrics
                <ArrowRight weight="bold" className="w-5 h-5" />
              </Link>
            </div>
          </FadeIn>
        </FadeInStagger>

        {/* Workflow Showcase Section */}
        <section className="space-y-12 pt-10">
          <div className="space-y-4 text-center mx-auto max-w-3xl flex flex-col items-center">
            <div className="inline-flex items-center px-3 py-1 rounded-lg bg-primary/10 text-primary w-fit font-mono text-xs font-bold uppercase tracking-widest mb-2">
              The Experience
            </div>
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-display font-extrabold text-foreground tracking-tight">
              From Prompt to Storybook.
            </h2>
            <p className="text-foreground/70 text-lg md:text-xl max-w-[60ch] leading-relaxed">
              Watch how our pipeline orchestrates open-weight models in real-time to convert a raw story input into a fully illustrated, safety-checked picture book.
            </p>
          </div>
          
          <WorkflowShowcase />
        </section>

        {/* Pipeline Section */}
        <section className="space-y-12 pt-24 border-t border-primary/15">
          <div className="space-y-4">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-display font-extrabold text-foreground tracking-tight">
              The Architecture
            </h2>
            <p className="text-foreground/70 text-lg md:text-xl max-w-[60ch] leading-relaxed">
              Our pipeline consists of 10 deterministic nodes. There is no autonomous routing; conditional edges exist only at moderation and consistency checkpoints. Explore the sequence below.
            </p>
          </div>
          
          <PipelineMap />
        </section>

        {/* Capstone Research Section */}
        <section className="relative flex flex-col md:flex-row gap-12 lg:gap-20 items-start pt-24 border-t border-primary/15">
          {/* Sticky Left: Title & Abstract */}
          <div className="md:w-5/12 md:sticky top-32 space-y-6">
            <div className="inline-flex items-center px-3 py-1 rounded-lg bg-secondary/20 text-secondary-deep font-mono text-xs font-bold uppercase tracking-widest">
              Capstone Context
            </div>
            <h2 className="text-4xl lg:text-5xl font-display font-extrabold text-foreground tracking-tight leading-[1.1]">
              The science behind the magic.
            </h2>
            <p className="text-foreground/70 text-lg leading-relaxed">
              StoryBuddy is built on rigorous quantitative-developmental research. These are the four core pillars driving our methodology and engineering decisions.
            </p>
          </div>

          {/* Scrolling Right: The 4 Pillars */}
          <div className="md:w-7/12 space-y-20 lg:space-y-32">
            {/* Pillar 1 */}
            <div className="space-y-5">
              <h3 className="text-3xl font-display font-bold text-foreground tracking-tight">1. Safety & Ethics by Design</h3>
              <p className="text-lg text-primary-deep leading-relaxed font-bold italic border-l-[3px] border-primary pl-5">
                &quot;Child safety isn&apos;t an afterthought or a cloud filter—it is structural and localized.&quot;
              </p>
              <div className="space-y-4 text-foreground/80 leading-relaxed text-lg">
                <p>When Grade 5–6 children author stories about their real lives, privacy cannot rely on black-box cloud defaults. StoryBuddy implements a localized, non-negotiable multi-stage safety stack.</p>
                <ul className="list-disc pl-5 space-y-3 marker:text-primary">
                  <li><strong>Localized PII Redaction:</strong> We deploy custom Filipino recognizers via Presidio to intercept localized names and address structures before storage or export.</li>
                  <li><strong>Dual Independent Classifiers:</strong> Chained safety gates run on both text (meta-llama/llama-guard-4-12b) and output images (qwen/qwen3-vl-32b-instruct + Gemma-3-27B rubric).</li>
                  <li><strong>Non-Punitive Failure States:</strong> System refusals present supportive, age-appropriate UI guidance so children are never penalized.</li>
                </ul>
              </div>
            </div>

            {/* Pillar 2 */}
            <div className="space-y-5">
              <h3 className="text-3xl font-display font-bold text-foreground tracking-tight">2. Open-Weight Mandate</h3>
              <p className="text-lg text-primary-deep leading-relaxed font-bold italic border-l-[3px] border-primary pl-5">
                &quot;Democratizing AI storytelling without per-seat licensing barriers.&quot;
              </p>
              <div className="space-y-4 text-foreground/80 leading-relaxed text-lg">
                <p>Proprietary model APIs create severe cost barriers and vendor lock-in, placing AI tools out of reach for provincial public schools. StoryBuddy runs entirely on open-weight models to ensure long-term reproducibility.</p>
                <ul className="list-disc pl-5 space-y-3 marker:text-primary">
                  <li><strong>100% Open-Weight Stack:</strong> Driven by Qwen3-32B, Qwen-Image-Edit, and Gemma-3-27B.</li>
                  <li><strong>Zero Per-Seat Vendor Fees:</strong> Self-hostable architecture designed so any school can deploy the platform on standard infrastructure.</li>
                  <li><strong>Architectural Sovereignty:</strong> Building with open weights forces safety and identity control into deterministic logic rather than relying on black-box promises.</li>
                </ul>
              </div>
            </div>

            {/* Pillar 3 */}
            <div className="space-y-5">
              <h3 className="text-3xl font-display font-bold text-foreground tracking-tight">3. Reason-Then-Score Validation</h3>
              <p className="text-lg text-primary-deep leading-relaxed font-bold italic border-l-[3px] border-primary pl-5">
                &quot;Eliminating generative identity drift to preserve the child&apos;s authentic story.&quot;
              </p>
              <div className="space-y-4 text-foreground/80 leading-relaxed text-lg">
                <p>Unconditioned image generators drift across pages. StoryBuddy turns character identity from a prompt-hoping gamble into deterministic application state.</p>
                <ul className="list-disc pl-5 space-y-3 marker:text-primary">
                  <li><strong>Reason-Then-Score VLM Judge:</strong> Evaluates generated scenes against canonical references using field-order discipline, preventing post-hoc rationalization.</li>
                  <li><strong>Targeted Regeneration:</strong> The extracted failure taxonomy feeds directly into a single, prompt-corrected retry.</li>
                  <li><strong>Story Memory:</strong> Main characters are rendered once up front. Subsequent scenes are strictly reference-conditioned.</li>
                </ul>
              </div>
            </div>

            {/* Pillar 4 */}
            <div className="space-y-5">
              <h3 className="text-3xl font-display font-bold text-foreground tracking-tight">4. Pre-Registered Methodology</h3>
              <p className="text-lg text-primary-deep leading-relaxed font-bold italic border-l-[3px] border-primary pl-5">
                &quot;Rigorous academic research, pre-registered plans, and a novel dataset contribution.&quot;
              </p>
              <div className="space-y-4 text-foreground/80 leading-relaxed text-lg">
                <p>StoryBuddy is built on quantitative-developmental research (Boehm&apos;s Spiral SDLC) backed by pre-registration. It addresses a critical void in current AI evaluation: identity retention for stylized, non-human characters.</p>
                <ul className="list-disc pl-5 space-y-3 marker:text-primary">
                  <li><strong>Addressing the Benchmark Gap:</strong> StoryBuddy builds and evaluates human pairwise identity judgments over invented non-human characters.</li>
                  <li><strong>Non-Circular Evaluation:</strong> The internal VLM judge never grades its own homework. Book acceptability is evaluated independently by an expert validation panel.</li>
                  <li><strong>Stage-Gated Risk Resolution:</strong> Early throwaway probes test fundamental assumptions against pre-declared kill criteria.</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}
