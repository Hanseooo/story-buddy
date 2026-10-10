// Mirrors GET /research/runs/{job_id}: backend/app/research.py:project_run. Change both together.

export type ModerationResult = { passed: boolean; categories: string[] };

export type RefVerdict = {
  differences_observed: string;
  contradictions: string[];
  matches_description: boolean;
  attributes_present: string[];
  text_free: boolean;
};

export type VlmVerdict = {
  differences_observed: string;
  same_character: boolean;
  attributes_present: string[];
  style_match: boolean;
  anatomy_intact: boolean;
  subjects_unique: boolean;
  text_free: boolean;
};

export type RunCharacter = {
  char_id: string;
  name: string;
  description: {
    species: string | null;
    colours: string[];
    body_features: string[];
    clothing: string[];
    notes: string | null;
    is_humanoid: boolean;
  };
  ref_image_url: string | null;
  ref_moderation_status: string | null;
  ref_verdict: RefVerdict | null;
  ref_verdict_prompt_version: number | null;
};

export type RunAttempt = {
  image_url: string | null;
  prompt: string | null;
  passed: boolean;
  failure_reasons: string[];
  vlm_verdict: VlmVerdict | null;
  scene_contradictions: string[] | null;
};

export type RunScene = {
  scene_id: string;
  text_excerpt: string;
  caption: string | null;
  visual_direction: string | null;
  characters_present: string[];
  objects_present: string[];
  moderation_status: string | null;
  regeneration_count: number;
  shipped_attempt: number | null;
  attempts: RunAttempt[];
};

export type RunStep = { node: string; started_at: string; duration_ms: number | null };

export type EndedOn = { node: string; kind: "failed" | "waiting" | "running" };

export type RunCost = {
  image_count: number;
  regen_count: number;
  usd_estimate: number;
  ref_retry_count: number;
  ref_mod_retry_count: number;
};

export type RunJob = {
  id: string;
  title: string | null;
  status: string;
  style_preset_id: string | null;
  created_at: string;
  failure_reason: string | null;
  langfuse_trace_url: string | null;
  usd_estimate: number | null;
  image_count: number | null;
  regen_count: number | null;
  ref_retry_count: number | null;
  scenes_total: number | null;
  scenes_passed: number | null;
  scenes_unchecked: number | null;
  approved: boolean;
};

export type RunDetail = {
  job: RunJob;
  checkpointed: boolean;
  story: { redacted_text: string | null; word_count: number; truncated: boolean } | null;
  steps: RunStep[];
  ended_on: EndedOn | null;
  moderation: { input: ModerationResult | null } | null;
  characters: RunCharacter[];
  scenes: RunScene[];
  cost: RunCost | null;
  // The projected StoryMemory, shown raw. `objects` and `locations` are read by name.
  state:
    | ({ objects?: { obj_id: string; name: string }[]; locations?: { loc_id: string; name: string }[] } & Record<
        string,
        unknown
      >)
    | null;
};
