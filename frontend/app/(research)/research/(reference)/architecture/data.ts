// SH-02, SH-08: every value below is read from a tracked source file, and data.test.ts fails when the
// source and this file disagree. Nothing here comes from the git-ignored training run record: its values
// were copied into hardware_and_hosting.md section 7, and that copy is the source.
export const SOURCES = {
  config: "backend/app/config.py",
  pyproject: "backend/pyproject.toml",
  packageJson: "frontend/package.json",
  hardware: "docs/capstone/hardware_and_hosting.md",
  techStack: "docs/TECH_STACK.md",
  runbook: "docs/capstone/research_runbook.md",
  architectureDoc: "docs/capstone/system_architecture.md",
  procfile: "backend/Procfile",
} as const;

export const DIAGRAM = {
  source: "docs/diagrams/drawio/system_architecture.drawio.svg",
  png: "/research/diagrams/system_architecture.png",
  asOf: "2026-11-21",
  alt: "System architecture as built on 2026-11-21. Browsers reach the Next.js frontend on Vercel. The frontend signs in with Supabase Auth and reads Postgres, Realtime and Storage. The FastAPI web service on Northflank redacts and moderates the title, then puts the job on a Redis queue. An RQ worker pulls the job, runs the LangGraph pipeline and calls OpenRouter and fal.ai. Sentry and Langfuse receive errors and traces.",
} as const;

// `mentions` is a literal the first file must contain, so a renamed or emptied file fails the test.
export const COMPONENTS = [
  { name: "Next.js frontend", role: "Pages for students, teachers and researchers. Runs on Vercel.", files: ["frontend/package.json"], mentions: '"next"' },
  { name: "Supabase Auth", role: "Password sign-in. The web service checks each request's Supabase token and role.", files: ["backend/app/auth.py"], mentions: "get_current_user" },
  { name: "Supabase Postgres, Storage and Realtime", role: "Job rows, classrooms and checkpoints. A private bucket for pictures. Job updates for the browser.", files: ["backend/app/db.py"], mentions: "create_client" },
  { name: "FastAPI web service", role: "Takes the story, runs the first checks, writes the job row and answers the pages' requests.", files: ["backend/app/main.py", "backend/Procfile"], mentions: "FastAPI(" },
  { name: "FastAPI to Redis enqueue", role: "Puts the job on the Redis queue named storybook. The web service does not run the pipeline.", files: ["backend/app/queue.py", "backend/app/main.py"], mentions: "Queue(" },
  { name: "RQ worker", role: "Pulls jobs from the queue and runs them. A second process on Northflank.", files: ["backend/worker/run_job.py", "backend/worker/run_worker.py"], mentions: "def run_storybook_job" },
  { name: "LangGraph pipeline", role: "The fixed sequence of steps that turns a story into a picture book.", files: ["backend/pipeline/graph.py"], mentions: "StateGraph" },
  { name: "OpenRouter", role: "Hosted open-weight text, judge and moderation models.", files: ["backend/providers.py", "backend/app/config.py"], mentions: "OpenAI(" },
  { name: "fal.ai", role: "Hosted open-weight image models. Draws the references and the pages.", files: ["backend/providers.py", "backend/app/config.py"], mentions: "fal_client" },
  { name: "Web-tier moderation and Presidio", role: "Before the job row is written, the web service redacts the title and checks it. In teacher review mode it redacts the story text too.", files: ["backend/app/main.py", "backend/providers.py"], mentions: "check_text" },
  { name: "Worker moderation", role: "Checks the story text and every picture before a child sees it.", files: ["backend/pipeline/input_gate.py", "backend/pipeline/char_ref_mod.py", "backend/pipeline/output_mod.py"], mentions: "classify_text_primary" },
  { name: "Langfuse", role: "Run traces from the worker.", files: ["backend/worker/run_job.py"], mentions: "Langfuse" },
  { name: "Sentry", role: "Error reports from the web service, sent only when a Sentry DSN is set. The frontend has the package but never starts it (there is no instrumentation file), and the worker does not use it.", files: ["backend/app/main.py"], mentions: "if settings.sentry_dsn_backend" },
  { name: "Research endpoint", role: "Gives researchers the run viewer's data. Needs a researcher account.", files: ["backend/app/research.py"], mentions: "research_router" },
  { name: "Teacher review", role: "A teacher approves or rejects each book. In teacher review mode a first moderation flag holds the job for the teacher.", files: ["backend/app/review.py", "backend/app/moderation_hold.py"], mentions: "def review_job" },
  { name: "Teacher notes", role: "A note from the teacher that the child can read.", files: ["backend/app/review_notes.py"], mentions: "child_notes_router" },
  { name: "Magic pencil", role: "The child writes a short change to a picture. The text is redacted and checked first.", files: ["backend/app/page_pencil.py"], mentions: "page_pencil_router" },
  { name: "PDF export", role: "Makes a PDF of an approved book when asked. Nothing is stored.", files: ["backend/app/pdf_export.py"], mentions: "pdf_router" },
] as const;

export const OWNER_TO_SUPPLY = "Owner to supply";

// The page reads each ID from the `setting` line of config.py.
export const MODELS = [
  { role: "Story text (analysis, scenes, prompts)", setting: "text_model", id: "mistralai/mistral-small-3.2-24b-instruct", host: "OpenRouter" },
  { role: "Judge, prompted (production)", setting: "vlm_judge_model", id: "google/gemma-3-27b-it", host: "OpenRouter" },
  { role: "Character reference picture", setting: "fal_image_model", id: "fal-ai/qwen-image", host: "fal.ai" },
  { role: "Page drawing (edits from the reference)", setting: "fal_image_edit_model", id: "fal-ai/qwen-image-edit-2511", host: "fal.ai" },
  { role: "Story text moderation, primary", setting: "moderation_primary_model", id: "meta-llama/llama-guard-4-12b", host: "OpenRouter" },
  { role: "Story text moderation, backstop", setting: "moderation_backstop_model", id: "openai/gpt-oss-safeguard-20b", host: "OpenRouter" },
  { role: "Picture moderation, primary", setting: "moderation_primary_image_model", id: "mistralai/mistral-small-3.2-24b-instruct", host: "OpenRouter" },
  { role: "Picture moderation, backstop", setting: "moderation_backstop_image_model", id: "google/gemma-3-27b-it", host: "OpenRouter" },
] as const;

// Python entries are declared ranges in pyproject.toml, so `version` is the range as written.
export const PYTHON_VERSION = ">=3.12";
export const BACKEND_LIBS = [
  { name: "fastapi", version: ">=0.115", role: "Web service" },
  { name: "langgraph", version: ">=0.2.45", role: "Pipeline" },
  { name: "pydantic", version: ">=2.9", role: "Data contracts" },
  { name: "redis", version: ">=5.2", role: "Queue client" },
  { name: "rq", version: ">=2.0", role: "Job queue" },
  { name: "supabase", version: ">=2.9.1", role: "Database client" },
  { name: "openai", version: ">=1.99", role: "Client for OpenRouter" },
  { name: "fal-client", version: ">=0.7", role: "Client for fal.ai" },
  { name: "presidio-analyzer", version: ">=2.2", role: "Finds personal information" },
  { name: "presidio-anonymizer", version: ">=2.2", role: "Redacts it" },
  { name: "spacy", version: ">=3.7", role: "Language model behind Presidio" },
  { name: "langfuse", version: ">=2.0", role: "Run traces" },
  { name: "sentry-sdk[fastapi]", version: ">=2.17", role: "Error reports" },
  { name: "weasyprint", version: ">=70,<71", role: "PDF export" },
] as const;

export const FRONTEND_LIBS = [
  { name: "next", version: "16.2.11", role: "App framework" },
  { name: "react", version: "19.2.4", role: "Interface" },
  { name: "react-dom", version: "19.2.4", role: "Interface" },
  { name: "@supabase/supabase-js", version: "^2.110.1", role: "Database and sign-in client" },
  { name: "@supabase/ssr", version: "^0.12.4", role: "Sign-in on the server" },
  { name: "@sentry/nextjs", version: "^10.64.0", role: "Error reports" },
  { name: "tailwindcss", version: "^4", role: "Styles" },
  { name: "vitest", version: "^4.1.10", role: "Tests" },
] as const;

// hardware_and_hosting.md section 7, copied there from the run record of the registered training.
export const TRAINING = [
  { item: "GPU", value: "NVIDIA RTX A6000, 49140 MiB (48 GB class), driver 580.178.04" },
  { item: "CUDA", value: "12.8" },
  { item: "Libraries", value: "bitsandbytes 0.50.2, Python 3.12.14" },
  { item: "Trainer", value: "LLaMA-Factory v0.9.5" },
  { item: "Base model", value: "Qwen/Qwen3.5-9B" },
  { item: "Recipe", value: "QLoRA, 4-bit bnb, LoRA rank 16, alpha 32" },
] as const;

export const HOSTING = [
  { item: "Frontend", value: "Vercel", source: "hardware" },
  { item: "Backend (web service, worker, Redis)", value: "Northflank, North America region, free tier", source: "hardware" },
  { item: "Database, sign-in, storage", value: "Supabase. Its region is not recorded in any tracked doc.", source: "hardware" },
  { item: "Models", value: "Hosted by OpenRouter and fal.ai. No model runs on the child's device.", source: "hardware" },
] as const;

// research_runbook.md names the card. The line moved from 549 to this line when the runbook grew.
export const RUNBOOK_GPU_LINE = 711;
export const DEV_HARDWARE = [
  { item: "Processor", value: OWNER_TO_SUPPLY },
  { item: "Memory", value: OWNER_TO_SUPPLY },
  { item: "Graphics card", value: "NVIDIA RTX 3050 Ti, 4 GB VRAM" },
  { item: "Storage", value: OWNER_TO_SUPPLY },
] as const;
