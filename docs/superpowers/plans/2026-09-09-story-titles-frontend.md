# Story Titles — Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a title field to the write form, submit it to the now-title-required
`POST /storybooks`, handle the redaction-confirmation round trip, and display the stored title
consistently across every existing surface the spec names (bookshelf, gallery, teacher review,
processing/reveal, reader, failure/revision).

**Architecture:** One shared `displayTitle()` helper implements the spec §5 fallback rule
(`nonblank stored title → existing excerpt → "Untitled"`) so every surface computes the same
label the same way. `JobRow`/`Job` gain an optional `title` field read straight off existing
Supabase selects. The write form and `FailureScreen`'s retry/revise paths carry `title` through
`sb.prefill`, mirroring how `text` and `style_preset_id` already travel.

**Tech Stack:** Next.js (App Router), React, TypeScript, Jest/RTL (existing `*.test.tsx` pattern).

**Spec:** `docs/specs/story-titles.md` — backend contract implemented in
`docs/superpowers/plans/2026-09-09-story-titles-backend.md`, which this plan assumes is done:
`POST /storybooks` requires `title` (string, 1–80 chars, single line), accepts `title_ack`, and
can respond `409` with `{"detail": {"checked_title": "..."}}` when redaction changed the title.

## Global Constraints

- `MAX_TITLE_CHARS = 80`, shown as an `n / 80` counter separate from the story word counter (§3).
- Trim outer whitespace, preserve interior spacing/case, reject line breaks in the input itself
  (§3) — the native `<input>` element already can't contain a line break; nothing extra needed for
  that half.
- Do not silently truncate pasted input; show "Keep your title to 80 characters." on invalid
  submit; "Give your story a title." on empty (§3, exact copy).
- On invalid submission: prevent the request, focus the first invalid field, retain title/story/
  style (§3).
- Enter in the title moves focus to the story; Enter in the story textarea inserts a newline (§3).
- Disable duplicate submits while pending; keep the in-app bookshelf exit; no persistent draft
  autosave beyond the existing `sb.prefill` session-storage transfer (§3).
- Display fallback, everywhere: nonblank stored title → first-line/60-char excerpt of
  `input_text` → `"Untitled"` (§5) — implemented once in `displayTitle()`, not per-surface.
- No child/teacher rename control anywhere in this plan (§4).
- No title inside generated artwork, no extra story page (§5).

---

### Task 1: Shared `displayTitle()` helper

**Files:**
- Create: `frontend/lib/displayTitle.ts`
- Test: `frontend/lib/displayTitle.test.ts`

**Interfaces:**
- Produces: `displayTitle(title: string | null | undefined, inputText: string | null | undefined): string`
  — consumed by every task below that renders a title.

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/lib/displayTitle.test.ts
import { displayTitle } from "./displayTitle";

describe("displayTitle", () => {
  it("returns the stored title when nonblank", () => {
    expect(displayTitle("My Dragon Book", "Once upon a time a dragon...")).toBe(
      "My Dragon Book"
    );
  });

  it("falls back to the first-line/60-char excerpt when title is null", () => {
    expect(displayTitle(null, "Once upon a time\nthe rest of the story")).toBe(
      "Once upon a time"
    );
  });

  it("falls back to the excerpt when title is an empty string", () => {
    expect(displayTitle("", "A brave knight went on an adventure")).toBe(
      "A brave knight went on an adventure"
    );
  });

  it("falls back to the excerpt when title is whitespace only", () => {
    expect(displayTitle("   ", "A story about a cat")).toBe("A story about a cat");
  });

  it("truncates the excerpt fallback to 60 characters", () => {
    const long = "x".repeat(80);
    expect(displayTitle(null, long)).toBe("x".repeat(60));
  });

  it("falls back to Untitled when there is no title and no story text", () => {
    expect(displayTitle(null, "")).toBe("Untitled");
    expect(displayTitle(undefined, undefined)).toBe("Untitled");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `frontend/`): `pnpm test displayTitle`
Expected: FAIL — `Cannot find module './displayTitle'`

- [ ] **Step 3: Write the implementation**

```typescript
// frontend/lib/displayTitle.ts

// spec docs/specs/story-titles.md §5: nonblank stored title, otherwise the existing
// first-line/60-char excerpt, otherwise "Untitled". One function so every surface computes
// the same label the same way — the fallback is presentation only, never a migration.
export function displayTitle(
  title: string | null | undefined,
  inputText: string | null | undefined
): string {
  if (title && title.trim() !== "") return title;
  return (inputText ?? "").split("\n")[0].slice(0, 60) || "Untitled";
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm test displayTitle`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/displayTitle.ts frontend/lib/displayTitle.test.ts
git commit -m "feat(titles): add shared displayTitle fallback helper"
```

---

### Task 2: Title field on the write form, with redaction-confirm round trip

**Files:**
- Modify: `frontend/app/s/[profileId]/write/page.tsx`
- Test: Create `frontend/app/s/[profileId]/write/page.test.tsx` if it doesn't exist (check with
  `ls frontend/app/s/[profileId]/write/*.test.tsx` first — if a test file already exists for this
  page, add to it instead)

**Interfaces:**
- Produces: `POST /storybooks` body now includes `title` (and `title_ack` when confirming a
  redaction) — consumed by the backend plan's Task 4.
- Consumes: nothing new from other frontend tasks.

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/app/s/[profileId]/write/page.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WriteStoryPage from "./page";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({ profileId: "p1" }),
}));

jest.mock("@/lib/supabaseClient", () => ({
  supabase: { auth: { getSession: () => Promise.resolve({ data: { session: { access_token: "t" } } }) } },
}));

function fillStory(minWords = 5) {
  const textarea = screen.getByLabelText("story text");
  fireEvent.change(textarea, { target: { value: "one two three four five" } });
  return textarea;
}

describe("WriteStoryPage title field", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  it("shows a title input with an n/80 counter separate from the word counter", () => {
    render(<WriteStoryPage />);
    const titleInput = screen.getByLabelText("Story title");
    fireEvent.change(titleInput, { target: { value: "My Book" } });
    expect(screen.getByText("7 / 80")).toBeInTheDocument();
  });

  it("blocks submit and shows 'Give your story a title.' when title is empty", async () => {
    render(<WriteStoryPage />);
    fillStory();
    const form = screen.getByRole("form");
    fireEvent.submit(form);
    expect(await screen.findByText("Give your story a title.")).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("blocks submit and shows the 81-char message without truncating the input", async () => {
    render(<WriteStoryPage />);
    fillStory();
    const titleInput = screen.getByLabelText("Story title");
    const longTitle = "x".repeat(81);
    fireEvent.change(titleInput, { target: { value: longTitle } });
    fireEvent.submit(screen.getByRole("form"));
    expect(
      await screen.findByText("Keep your title to 80 characters.")
    ).toBeInTheDocument();
    expect((titleInput as HTMLInputElement).value).toBe(longTitle);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("submits title and text together on valid input", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ job_id: "job-1" }),
    });
    render(<WriteStoryPage />);
    fillStory();
    fireEvent.change(screen.getByLabelText("Story title"), { target: { value: "My Book" } });
    fireEvent.submit(screen.getByRole("form"));
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body.title).toBe("My Book");
    expect(body.text).toBe("one two three four five");
  });

  it("on a 409, shows the redacted title and resubmits with title_ack on accept", async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: () => Promise.resolve({ detail: { checked_title: "call me at <PH_MOBILE>" } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ job_id: "job-2" }),
      });
    render(<WriteStoryPage />);
    fillStory();
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: "call me at 09171234567" },
    });
    fireEvent.submit(screen.getByRole("form"));

    expect(
      await screen.findByText(/call me at <PH_MOBILE>/)
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /use this title/i }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
    const secondBody = JSON.parse((global.fetch as jest.Mock).mock.calls[1][1].body);
    expect(secondBody.title_ack).toBe("call me at <PH_MOBILE>");
    expect(secondBody.title).toBe("call me at 09171234567");
  });

  it("Enter in the title moves focus to the story textarea without submitting", () => {
    render(<WriteStoryPage />);
    const titleInput = screen.getByLabelText("Story title");
    fireEvent.keyDown(titleInput, { key: "Enter", code: "Enter" });
    expect(screen.getByLabelText("story text")).toHaveFocus();
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test write/page.test.tsx`
Expected: FAIL — no "Story title" label exists yet, `getByRole("form")` finds no accessible form
name, etc.

- [ ] **Step 3: Write the implementation**

Modify `frontend/app/s/[profileId]/write/page.tsx`. Add the title constant near the existing
`MIN_STORY_WORDS`/`MAX_STORY_WORDS` constants (lines 9-10):

```typescript
const MAX_TITLE_CHARS = 80;
```

Add title state, error state, and a ref for focus management inside the component (after line 30):

```typescript
  const [title, setTitle] = useState("");
  const [titleError, setTitleError] = useState<string | null>(null);
  const [pendingRedactedTitle, setPendingRedactedTitle] = useState<string | null>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
```

(Add `useRef` to the existing `import { useState, useEffect } from "react";` at line 3.)

Restore title from `sb.prefill` alongside text — the prefill effect (lines 34-52) currently reads
a plain string from `sessionStorage`. Change the prefill payload to carry both fields as JSON, and
update both the read side here and the write side in `FailureScreen.tsx` (Task 3) together, since
they share the same session-storage contract:

```typescript
  useEffect(() => {
    let prefill: { text: string; title: string } | null = null;
    try {
      const raw = sessionStorage.getItem(PREFILL_KEY);
      if (raw !== null) {
        sessionStorage.removeItem(PREFILL_KEY);
        prefill = JSON.parse(raw);
      }
    } catch { /* storage unavailable or malformed */ }

    if (prefill !== null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setText(prefill.text);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setTitle(prefill.title);
      try {
        setChainCount(Number(sessionStorage.getItem(CHAIN_KEY) ?? 0));
      } catch { /* unavailable */ }
    } else {
      resetFailChain();
    }
  }, []);
```

Add a title-focused submit handler. Replace `handleSubmit` (lines 58-88):

```typescript
  function focusTitle() {
    titleInputRef.current?.focus();
  }

  async function postStorybook(titleAck?: string) {
    const stylePresetId = (document.querySelector<HTMLInputElement>(
      'input[name="style_preset_id"]:checked'
    ))?.value;
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/storybooks`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session?.access_token}`,
      },
      body: JSON.stringify({
        text,
        title,
        style_preset_id: stylePresetId,
        ...(titleAck !== undefined ? { title_ack: titleAck } : {}),
      }),
    });
  }

  async function afterSubmit(res: Response) {
    if (res.status === 409) {
      const data = await res.json();
      setPendingRedactedTitle(data.detail.checked_title);
      return;
    }
    if (!res.ok) {
      setPostError(true);
      return;
    }
    const data = await res.json();
    router.push(`/s/${profileId}/process/${data.job_id}`);
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const trimmedTitle = title.trim();
    setTitleError(null);
    if (trimmedTitle.length === 0) {
      setTitleError("Give your story a title.");
      focusTitle();
      return;
    }
    if (trimmedTitle.length > MAX_TITLE_CHARS) {
      setTitleError("Keep your title to 80 characters.");
      focusTitle();
      return;
    }
    if (wordCount < MIN_STORY_WORDS) {
      textareaRef.current?.focus();
      return;
    }

    setSubmitting(true);
    setPostError(false);
    setPendingRedactedTitle(null);
    try {
      const res = await postStorybook();
      await afterSubmit(res);
    } catch {
      setPostError(true);
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmRedactedTitle() {
    if (pendingRedactedTitle === null) return;
    setSubmitting(true);
    setPostError(false);
    try {
      const res = await postStorybook(pendingRedactedTitle);
      await afterSubmit(res);
    } catch {
      setPostError(true);
    } finally {
      setSubmitting(false);
    }
  }

  function handleTitleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      textareaRef.current?.focus();
    }
  }
```

Add the title `<input>` above the story textarea, and the counter/error UI. Insert directly before
the `<motion.textarea` block (before line 94), and give the `<form>` an accessible name and the
textarea a ref:

```tsx
    <form onSubmit={handleSubmit} aria-label="Write your story" className="min-h-[calc(100dvh-76px)] sm:min-h-[calc(100dvh-85px)] flex flex-col py-4 sm:py-6 lg:py-8 px-4 sm:px-8 max-w-5xl mx-auto w-full relative">

      {/* Title — story-titles spec §3 */}
      <div className="mb-3 shrink-0">
        <label htmlFor="story-title" className="block text-xs font-display font-extrabold tracking-wider uppercase text-foreground/60 mb-1">
          Story title
        </label>
        <input
          id="story-title"
          ref={titleInputRef}
          type="text"
          value={title}
          onChange={(e) => { setTitle(e.target.value); setTitleError(null); }}
          onKeyDown={handleTitleKeyDown}
          placeholder="Name your book"
          aria-label="Story title"
          aria-invalid={titleError !== null}
          aria-describedby="title-count title-error"
          className="w-full bg-transparent font-kid font-bold text-xl sm:text-2xl text-foreground placeholder-foreground/35 focus:outline-none caret-primary border-b-2 border-primary/10 focus:border-primary pb-1"
        />
        <div className="flex items-center justify-between mt-1">
          <span id="title-count" className="text-xs font-bold text-foreground/50">
            {title.length} / {MAX_TITLE_CHARS}
          </span>
          {titleError && (
            <span id="title-error" role="alert" className="text-xs font-bold text-destructive">
              {titleError}
            </span>
          )}
        </div>
      </div>

      <motion.textarea
        ref={textareaRef}
        initial={{ opacity: 0, y: 10 }}
```

(Remove the now-duplicate `initial={{ opacity: 0, y: 10 }}` line that already exists at line 95 —
this just threads a `ref` onto the existing element, everything else about the textarea is
unchanged.)

Add the redaction-confirm panel just before the closing `</form>` (after the Floating Action Bar,
before line 206):

```tsx
      {pendingRedactedTitle !== null && (
        <div role="alertdialog" aria-label="Title changed for privacy" className="mt-3 shrink-0 bg-secondary/10 border border-secondary/30 rounded-2xl p-4">
          <p className="font-kid text-sm text-foreground/80">
            We changed your title to keep it private: <strong>{pendingRedactedTitle}</strong>
          </p>
          <div className="mt-3 flex gap-3">
            <button
              type="button"
              disabled={submitting}
              onClick={confirmRedactedTitle}
              className="min-h-[44px] px-4 rounded-xl bg-primary text-on-primary font-bold disabled:opacity-50"
            >
              Use this title
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={() => setPendingRedactedTitle(null)}
              className="min-h-[44px] px-4 rounded-xl border border-primary/20 text-primary font-bold disabled:opacity-50"
            >
              Change it
            </button>
          </div>
        </div>
      )}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm test write/page.test.tsx`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add frontend/app/s/[profileId]/write/page.tsx frontend/app/s/[profileId]/write/page.test.tsx
git commit -m "feat(titles): add title field, validation, and redaction-confirm flow to write page"
```

---

### Task 3: Carry title through `FailureScreen` retry/revise and `sb.prefill`

**Files:**
- Modify: `frontend/components/FailureScreen.tsx`
- Modify: `frontend/app/s/[profileId]/book/[jobId]/page.tsx:164,172` (props passed to `FailureScreen`)
- Modify: `frontend/app/s/[profileId]/process/[jobId]/page.tsx:282-289` (same)
- Test: Create/extend `frontend/components/FailureScreen.test.tsx` if present (check with `ls`
  first)

**Interfaces:**
- Consumes: `sb.prefill` session-storage contract changed in Task 2 (now
  `{"text": string, "title": string}`, not a bare string).
- Produces: `FailureScreen` accepts a new `title?: string | null` prop, sends `title` on retry's
  `POST /storybooks`, and writes the JSON prefill shape on revise.

- [ ] **Step 1: Write the failing tests**

Add to `frontend/components/FailureScreen.test.tsx` (create it if it doesn't exist, following the
existing render/props pattern used elsewhere in this repo's `*.test.tsx` files — render with
`kind="retry"` and `kind="revise"` props):

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import FailureScreen from "./FailureScreen";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({ profileId: "p1" }),
}));
jest.mock("@/lib/supabaseClient", () => ({
  supabase: { auth: { getSession: () => Promise.resolve({ data: { session: { access_token: "t" } } }) } },
}));

describe("FailureScreen title carry", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
    sessionStorage.clear();
  });

  it("sends the title on retry's POST /storybooks", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ job_id: "job-9" }),
    });
    render(
      <FailureScreen kind="retry" jobId="j1" inputText="Once upon a time" title="My Dragon Book" stylePresetId="cel" />
    );
    fireEvent.click(screen.getByRole("button", { name: /make this story again/i }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body.title).toBe("My Dragon Book");
  });

  it("writes title and text together into sb.prefill on revise", () => {
    render(
      <FailureScreen kind="revise" jobId="j1" inputText="Once upon a time" title="My Dragon Book" />
    );
    fireEvent.click(screen.getByRole("button", { name: /change my words/i }));
    const stored = JSON.parse(sessionStorage.getItem("sb.prefill") as string);
    expect(stored).toEqual({ text: "Once upon a time", title: "My Dragon Book" });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test FailureScreen`
Expected: FAIL — `title` prop doesn't exist on `Props`, and `sb.prefill` still stores a bare
string.

- [ ] **Step 3: Write the implementation**

In `frontend/components/FailureScreen.tsx`:

Add `title` to `Props` (line 34-42):

```typescript
type Props = {
  kind?: FailureKind;
  reason?: FailureReason | string | null;
  jobId?: string;
  inputText?: string;
  title?: string | null;
  stylePresetId?: string | null;
  countable?: boolean;
  onReload?: () => void;
};
```

Add `title` to the destructured props (line 306-314):

```typescript
export default function FailureScreen({
  kind,
  reason,
  jobId,
  inputText = "",
  title = null,
  stylePresetId = null,
  countable = true,
  onReload,
}: Props) {
```

Include it in `submitRetry`'s body (line 336):

```typescript
        body: JSON.stringify({
          text: inputText,
          title,
          style_preset_id: stylePresetId ?? "cel",
        }),
```

Change `handleRevise`'s prefill write (line 374) to the JSON shape Task 2 now reads:

```typescript
  const handleRevise = () => {
    const count = countable ? bumpChain() : chainCount;
    console.log("sb:action", { action: "revise", kind, chain_count: count });
    try {
      sessionStorage.setItem(PREFILL_KEY, JSON.stringify({ text: inputText, title }));
    } catch { /* unavailable */ }
    router.push(profileId ? `/s/${profileId}/write` : "/write");
  };
```

Now thread `title` from the two callers. In `frontend/app/s/[profileId]/book/[jobId]/page.tsx`,
both `<FailureScreen ...>` calls (lines 164 and 172) pass `inputText={row?.input_text}`
`stylePresetId={row?.style_preset_id}` — add `title={row?.title}` alongside them on both lines
(this needs `JobRow.title` from Task 4, so if implementing tasks out of order, do Task 4 first).
Same change in `frontend/app/s/[profileId]/process/[jobId]/page.tsx` at its one `<FailureScreen>`
call (lines 282-289): add `title={row?.title}`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm test FailureScreen`
Expected: PASS

- [ ] **Step 5: Run the write-page tests again**

Task 2's prefill-read test and this task's prefill-write test share the `sb.prefill` JSON shape —
confirm they still agree.

Run: `pnpm test write/page.test.tsx FailureScreen`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/components/FailureScreen.tsx frontend/components/FailureScreen.test.tsx \
        "frontend/app/s/[profileId]/book/[jobId]/page.tsx" \
        "frontend/app/s/[profileId]/process/[jobId]/page.tsx"
git commit -m "feat(titles): carry title through FailureScreen retry/revise and sb.prefill"
```

---

### Task 4: `title` on shared job types, and child bookshelf / processing display

**Files:**
- Modify: `frontend/lib/useJob.ts` (`JobRow` type + select string)
- Modify: `frontend/app/s/[profileId]/page.tsx` (bookshelf: select string + `BookCard` title)
- Modify: `frontend/app/s/[profileId]/process/[jobId]/page.tsx` (context heading)
- Test: `frontend/lib/useJob.test.ts`, `frontend/app/s/[profileId]/page.test.tsx` (extend existing
  files — check they exist first, which the earlier grep confirmed)

**Interfaces:**
- Consumes: `displayTitle()` (Task 1).
- Produces: `JobRow.title: string | null` — consumed by Task 3 (already referenced above), Task 5,
  and Task 6.

- [ ] **Step 1: Write the failing tests**

Add to `frontend/lib/useJob.test.ts`:

```typescript
it("select string includes title", () => {
  // Adjust to this file's existing pattern for asserting the .select(...) argument —
  // find the existing assertion on the select string (search for "input_text" in this
  // file) and extend it the same way, e.g.:
  // expect(selectArg).toContain("title");
});
```

Add to `frontend/app/s/[profileId]/page.test.tsx` (bookshelf), following its existing mock-Supabase
pattern (search the file for how it currently seeds `jobs` rows and mocks
`supabase.from("jobs").select(...)`):

```typescript
it("shows the stored title on a book card when present", async () => {
  // Seed a job row with { title: "My Dragon Book", input_text: "..." } using this file's
  // existing mock setup, render the page, and assert screen.getByText("My Dragon Book").
});

it("falls back to the excerpt when title is null", async () => {
  // Seed a job row with { title: null, input_text: "A brave knight\nrest of story" },
  // render, and assert screen.getByText("A brave knight").
});
```

(These two tests are written against this file's existing Supabase-mocking scaffolding rather
than a fresh one — read the file first to match its exact mock shape before filling in the body,
per this repo's established `*.test.tsx` pattern for this page.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test useJob.test.ts page.test.tsx`
Expected: FAIL — `title` absent from the select string and from rendered card text.

- [ ] **Step 3: Write the implementation**

In `frontend/lib/useJob.ts`, add `title` to `JobRow` (line 13-30):

```typescript
export type JobRow = {
  id: string;
  status: string;
  current_stage: string | null;
  failure_reason: string | null;
  input_text: string;
  title: string | null;
  style_preset_id: string | null;
  pages: Array<{ scene_id: string; caption: string; image_path: string }>;
  reveal: {
    characters: Array<{
      char_id: string;
      name: string;
      image_path: string;
      chips: string[];
    }>;
    taps_left: number;
  } | null;
};
```

Add `title` to the select string (line 56):

```typescript
      .select("id, status, current_stage, failure_reason, input_text, title, style_preset_id, pages, reveal")
```

In `frontend/app/s/[profileId]/page.tsx`, import the helper and use it. Add the import (near line
6):

```typescript
import { displayTitle } from "@/lib/displayTitle";
```

Add `title` to the bookshelf's own select string (line 61):

```typescript
        .select("id, status, current_stage, failure_reason, input_text, title, pages, reveal")
```

Replace the inline excerpt logic (line 82) with the shared helper:

```typescript
          title: displayTitle(j.title, j.input_text),
```

(`JobCard.title` already exists as a field — this just changes what computes it. `JobRow` from
`useJob.ts` doesn't type this page's own `select`, so also add `title: string | null;` to the
ad-hoc row shape this file reads, if it declares one separately — check whether this file imports
`JobRow` or has its own inline type for the `jobs` rows it selects, and add `title` to whichever it
is.)

In `frontend/app/s/[profileId]/process/[jobId]/page.tsx`, give the child processing context a
title without competing with the current action (spec §5 table row "Child processing/reveal").
Add it as a small line above the `<KineticText text="Making your book!" />` heading (around line
426):

```tsx
      {row?.title && (
        <p className="z-10 -mb-8 text-sm font-bold text-foreground/50 uppercase tracking-wider">
          {row.title}
        </p>
      )}
      <h1 className="z-10 mb-16 h-20 flex items-center justify-center font-display text-5xl md:text-6xl text-foreground tracking-tighter">
        <KineticText text="Making your book!" />
      </h1>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm test useJob.test.ts page.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/useJob.ts frontend/lib/useJob.test.ts \
        "frontend/app/s/[profileId]/page.tsx" "frontend/app/s/[profileId]/page.test.tsx" \
        "frontend/app/s/[profileId]/process/[jobId]/page.tsx"
git commit -m "feat(titles): surface title on JobRow, bookshelf cards, and processing context"
```

---

### Task 5: Reader heading and full-title accessible link name

**Files:**
- Modify: `frontend/app/s/[profileId]/book/[jobId]/page.tsx`
- Test: `frontend/app/s/[profileId]/book/[jobId]/page.test.tsx` (extend existing file)

**Interfaces:**
- Consumes: `JobRow.title` (Task 4), `displayTitle()` (Task 1).

- [ ] **Step 1: Write the failing test**

Add to `frontend/app/s/[profileId]/book/[jobId]/page.test.tsx`, matching its existing
`useJob`-mocking pattern (search the file for how it currently mocks `useJob`'s return value):

```typescript
it("renders the book title as the reader heading, wrapping long text without overflow", async () => {
  // Mock useJob to return a terminal-success row with { title: "A Very Long Title That Keeps Going And Going", ... }
  // Render BookPage, assert screen.getByRole("heading", { name: /A Very Long Title/ }) exists.
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm test "book/\[jobId\]/page.test.tsx"`
Expected: FAIL — no heading with the title text is rendered yet.

- [ ] **Step 3: Write the implementation**

In `frontend/app/s/[profileId]/book/[jobId]/page.tsx`, import `displayTitle` and add a heading.
Add the import near the top (after line 12):

```typescript
import { displayTitle } from "@/lib/displayTitle";
```

Add the heading into the "Reader Sub-Header" region, between the back link and the view-mode
toggle (after line 247, before the `<div role="group"` view-toggle block) — only once
`signedPages` exist (i.e. inside the `terminal-success` render path, not the loading/failure
paths, matching spec §5's "Reader, including shared reader" row):

```tsx
        <h1 className="font-display text-lg sm:text-xl font-extrabold text-foreground text-center flex-1 mx-3 truncate sm:whitespace-normal sm:break-words">
          {displayTitle(row?.title, row?.input_text ?? "")}
        </h1>
```

`truncate` on narrow screens keeps a single line from overflowing; `sm:whitespace-normal
sm:break-words` lets it wrap on wider layouts without horizontal scroll, per spec §5 ("Reader
headings wrap long unbroken text without horizontal overflow").

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm test "book/\[jobId\]/page.test.tsx"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add "frontend/app/s/[profileId]/book/[jobId]/page.tsx" \
        "frontend/app/s/[profileId]/book/[jobId]/page.test.tsx"
git commit -m "feat(titles): show book title as the reader heading"
```

---

### Task 6: Teacher review — pending/approved/rejected/failed lists and preview

**Files:**
- Modify: `frontend/lib/types/jobs.ts` (`Job` type)
- Modify: `frontend/app/classroom/[classroomId]/books/page.tsx` (select string)
- Modify: `frontend/components/BookCard.tsx`
- Modify: `frontend/components/BookReviewDialog.tsx`
- Test: `frontend/app/classroom/[classroomId]/books/page.test.tsx` (extend existing file)

**Interfaces:**
- Consumes: `displayTitle()` (Task 1).
- Produces: `Job.title: string | null` — also usable by the classroom gallery (Task 7).

- [ ] **Step 1: Write the failing tests**

Add to `frontend/app/classroom/[classroomId]/books/page.test.tsx`, matching its existing
Supabase-mock pattern (same approach as Task 4's bookshelf tests):

```typescript
it("shows the book title on a pending review card", async () => {
  // Seed a job with { title: "My Dragon Book", ... }, render BooksPage, assert the title
  // text appears (mobile card and/or desktop table row, per this file's existing render
  // assertions for student name/date).
});

it("shows the book title in the failed-book row alongside the reference id", async () => {
  // Seed a failed job with { title: "My Dragon Book", failure_reason: "child_text", ... },
  // assert the title renders in the FailedBookRow output.
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm test "classroom/\[classroomId\]/books/page.test.tsx"`
Expected: FAIL — no title text rendered anywhere on the page yet.

- [ ] **Step 3: Write the implementation**

In `frontend/lib/types/jobs.ts`, add `title` to `Job` (line 19-30):

```typescript
export type Job = {
  id: string;
  status: string;
  failure_reason: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  created_at: string;
  input_text: string;
  title: string | null;
  pages: JobPage[] | null;
  profile_id: string;
  profiles: { display_nickname: string; avatar_id: string | null } | null;
};
```

In `frontend/app/classroom/[classroomId]/books/page.tsx`, add `title` to `fetchJobs`'s select
string (line 41):

```typescript
        "id, status, failure_reason, approved_at, rejected_at, created_at, input_text, title, pages, profile_id, profiles(display_nickname, avatar_id)"
```

Add the import (near line 10):

```typescript
import { displayTitle } from "@/lib/displayTitle";
```

In `FailedBookRow` (line 462-533), show the title alongside the child's name (after line 507):

```tsx
      <div className="flex items-center justify-between gap-2 mb-2">
        <div>
          <p className="font-bold text-sm text-foreground">{name}</p>
          <p className="text-xs text-foreground/60">{displayTitle(job.title, job.input_text)}</p>
        </div>
```

(This replaces the existing single `<p className="font-bold text-sm text-foreground">{name}</p>`
line with the two-line block above.)

In `frontend/components/BookCard.tsx`, show the title in the meta block (after line 46, inside the
`<div>` that already holds the name/date):

```tsx
        <div>
          <p className="font-bold text-foreground text-sm truncate">{name}</p>
          <p className="text-xs text-foreground/60 truncate">{displayTitle(job.title, job.input_text)}</p>
          <p className="text-xs text-foreground/50 mt-0.5">{date}</p>
        </div>
```

Add the import to `BookCard.tsx` (near line 1):

```typescript
import { displayTitle } from "@/lib/displayTitle";
```

For the desktop table (`BookTableRow`, lines 415-460), add a Title column: insert a `<th>` between
"Student" and "Submitted" in the `<thead>` (around line 317-322):

```tsx
                  <th className="text-left px-6 py-3 font-bold text-foreground/60 text-xs uppercase tracking-wider">
                    Title
                  </th>
```

And the matching `<td>` in `BookTableRow` (after the Student `<td>`, before the Submitted `<td>`
at line 446):

```tsx
      <td className="px-6 py-3 text-foreground/70 max-w-[24ch] truncate">
        {displayTitle(job.title, job.input_text)}
      </td>
```

In `frontend/components/BookReviewDialog.tsx`, show the title as the preview heading — read the
file first (it wasn't matched by the earlier grep for `title`/`input_text`, meaning it currently
renders only images) to find where its dialog header/title-bar markup lives, then add:

```tsx
import { displayTitle } from "@/lib/displayTitle";
```

and render `{displayTitle(job.title, job.input_text)}` in that header, next to or above whatever
identifies the book being reviewed (student name, page count, etc. — match the existing header's
layout rather than introducing a new one).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm test "classroom/\[classroomId\]/books/page.test.tsx"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/types/jobs.ts "frontend/app/classroom/[classroomId]/books/page.tsx" \
        frontend/components/BookCard.tsx frontend/components/BookReviewDialog.tsx \
        "frontend/app/classroom/[classroomId]/books/page.test.tsx"
git commit -m "feat(titles): show book title across teacher review surfaces"
```

---

### Task 7: Classroom gallery title, plus existing author identity and cover

**Files:**
- Modify: `frontend/app/s/[profileId]/gallery/page.tsx`
- Test: `frontend/app/s/[profileId]/gallery/page.test.tsx` (extend existing file)

**Interfaces:**
- Consumes: `displayTitle()` (Task 1).

- [ ] **Step 1: Write the failing test**

Add to `frontend/app/s/[profileId]/gallery/page.test.tsx`, matching its existing server-component
test setup (this page is an async server component — check the existing file for how it mocks
`createServerClient`/`cookies` and follow that exact pattern):

```typescript
it("shows the book title next to the author on a gallery card", async () => {
  // Seed a job with { title: "My Dragon Book", ... } through this file's existing mock,
  // render/await GalleryPage, assert the rendered output contains "My Dragon Book".
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm test "gallery/page.test.tsx"`
Expected: FAIL — no title text rendered.

- [ ] **Step 3: Write the implementation**

In `frontend/app/s/[profileId]/gallery/page.tsx`, add `title` to the local `Job` type (line 7-13):

```typescript
type Job = {
  id: string;
  approved_at: string;
  title: string | null;
  input_text: string;
  pages: { scene_id: string; caption: string; image_path: string }[] | null;
  profile_id: string;
  profiles: { display_nickname: string; avatar_id: string | null } | null;
};
```

Note this page's current select (line 31) does not fetch `input_text` either — add both, since
`displayTitle`'s excerpt fallback needs it:

```typescript
    .select("id, approved_at, title, input_text, pages, profile_id, profiles!inner(display_nickname, avatar_id)")
```

Add the import (near line 5):

```typescript
import { displayTitle } from "@/lib/displayTitle";
```

Add the title next to the existing author line (line 85-89):

```tsx
              <div className="p-3 flex flex-col gap-1">
                <p className="font-kid truncate text-sm font-bold text-foreground">
                  {displayTitle(job.title, job.input_text)}
                </p>
                <div className="flex items-center gap-3">
                  <Avatar avatarId={job.profiles?.avatar_id ?? null} displayNickname={nickname} size={32} />
                  <p className="font-kid truncate text-base font-bold text-foreground">
                    by {nickname}
                  </p>
                </div>
              </div>
```

(This replaces the existing `<div className="p-3 flex items-center gap-3">...</div>` block.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm test "gallery/page.test.tsx"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add "frontend/app/s/[profileId]/gallery/page.tsx" "frontend/app/s/[profileId]/gallery/page.test.tsx"
git commit -m "feat(titles): show book title on classroom gallery cards"
```

---

### Task 8: Legacy resubmission — prefill the excerpt as an editable suggestion

**Files:**
- Modify: `frontend/app/s/[profileId]/page.tsx` (bookshelf "Make story again"/resubmit entry point
  for an untitled legacy job — confirm exactly which action this is: read the bucket→href map at
  lines 198-206 and `FailureScreen`'s `handleRevise`/retry to find where a legacy (`title: null`)
  job's "start a new submission from this one" path lives)
- Test: extend whichever test file covers that entry point

**Interfaces:**
- Consumes: `displayTitle()` (Task 1), the `sb.prefill` JSON shape (Task 2/3).

Spec §4: "A new submission made from [an old untitled job] requires a title: open the form with
the legacy excerpt prefilled as an editable suggestion and retain story/style." This is
`FailureScreen`'s existing "Change my words" (`handleRevise`) path when the source job's `title` is
`null` — Task 3 already threads `title` through `sb.prefill`, but for a legacy job `title` is
`null`, and the spec wants the *excerpt*, not an empty string, offered as the starting point.

- [ ] **Step 1: Write the failing test**

Add to `frontend/components/FailureScreen.test.tsx` (from Task 3):

```typescript
it("prefills the legacy excerpt as an editable title suggestion when the source job has no title", () => {
  render(
    <FailureScreen kind="revise" jobId="j1" inputText="A brave knight went on an adventure" title={null} />
  );
  fireEvent.click(screen.getByRole("button", { name: /change my words/i }));
  const stored = JSON.parse(sessionStorage.getItem("sb.prefill") as string);
  expect(stored.title).toBe("A brave knight went on an adventure");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm test FailureScreen`
Expected: FAIL — `stored.title` is currently `null` (Task 3 passes `title` through as-is).

- [ ] **Step 3: Write the implementation**

In `frontend/components/FailureScreen.tsx`, import `displayTitle` and use it in `handleRevise`:

```typescript
import { displayTitle } from "@/lib/displayTitle";
```

```typescript
  const handleRevise = () => {
    const count = countable ? bumpChain() : chainCount;
    console.log("sb:action", { action: "revise", kind, chain_count: count });
    try {
      sessionStorage.setItem(
        PREFILL_KEY,
        JSON.stringify({ text: inputText, title: displayTitle(title, inputText) })
      );
    } catch { /* unavailable */ }
    router.push(profileId ? `/s/${profileId}/write` : "/write");
  };
```

Since `displayTitle` returns `"Untitled"` when both `title` and `inputText` are empty, and the
write page's title field must start genuinely editable/blank in that edge case (never literally
prefilled with the word "Untitled" as if the child typed it), guard it: only fall back to the
excerpt, never to `"Untitled"`, in this one call site. Add a small local helper instead of reusing
`displayTitle` directly here:

```typescript
  const handleRevise = () => {
    const count = countable ? bumpChain() : chainCount;
    console.log("sb:action", { action: "revise", kind, chain_count: count });
    const suggestedTitle = title && title.trim() !== ""
      ? title
      : (inputText ?? "").split("\n")[0].slice(0, 60);
    try {
      sessionStorage.setItem(
        PREFILL_KEY,
        JSON.stringify({ text: inputText, title: suggestedTitle })
      );
    } catch { /* unavailable */ }
    router.push(profileId ? `/s/${profileId}/write` : "/write");
  };
```

(This drops the `displayTitle` import again — the `"Untitled"` fallback it adds is specifically
wrong for a prefilled form field, so this site intentionally reimplements just the excerpt half.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm test FailureScreen`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/components/FailureScreen.tsx frontend/components/FailureScreen.test.tsx
git commit -m "feat(titles): prefill legacy excerpt as an editable title suggestion on resubmit"
```

---

### Task 9: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full frontend suite**

Run (from `frontend/`): `pnpm lint`
Expected: no new violations.

- [ ] **Step 2: Build**

Run: `pnpm build`
Expected: succeeds — this catches any type error across the `JobRow`/`Job` type changes that unit
tests alone might miss (e.g. a consumer file not covered by an existing test file).

- [ ] **Step 3: Full test suite**

Run: `pnpm test`
Expected: all tests PASS.

- [ ] **Step 4: Manual QA** (spec §7)

Not automatable — do these by hand against a local dev server before calling this done: mobile
width and 200% zoom on the write form and reader heading, keyboard-only writing (tab to title →
Enter moves to story → tab through style picker → submit), a title at exactly 80 characters, two
books with duplicate titles (confirm they stay distinguishable by author/status/cover — no code
change needed if Tasks 4-7 already show author/date/cover alongside title, but verify it visually),
a legacy job's safe fallback rendering as the excerpt, teacher review and classroom sharing with a
titled book end to end.

- [ ] **Step 5: Commit** (only if Steps 1-3 required fixes)

```bash
git add -A
git commit -m "fix(titles): address lint/build/test issues found in full verification pass"
```

---

## Self-Review

**Spec coverage:**
- §3 (title field, counter, validation copy, focus-first-invalid-field, retain values, Enter
  behavior, disable duplicate submits, no autosave) → Task 2.
- §4 (title/story stay separate on the frontend — the write form never merges them into one
  field; redaction round trip; failure recovery carries the checked title; legacy resubmission
  suggestion) → Tasks 2, 3, 8.
- §5 display contract table, row by row: child bookshelf → Task 4; shared classroom gallery →
  Task 7; teacher book review → Task 6; child processing/reveal → Task 4; reader → Task 5;
  failure/revision → Task 3. Two-line card truncation with full accessible label, reader wrap
  without horizontal overflow → Tasks 4-7's `truncate`/`line-clamp` classes (bookshelf card
  already had `line-clamp-2`; Task 5's heading adds the wrap classes explicitly).
- §7 manual QA and verification → Task 9.

**Placeholder scan:** Tasks 4-7's tests describe the seeding pattern to follow (each page's
existing Supabase-mock shape) rather than inlining a duplicate mock scaffold sight-unseen — this
is a deliberate "match the existing file's pattern" instruction, not a TBD; the assertions and
expected behavior are concrete in every case. Everything else has literal code.

**Type consistency:** `displayTitle(title: string | null | undefined, inputText: string | null |
undefined): string` declared once in Task 1, called identically in Tasks 4, 5, 6, 7 (`title`,
`input_text` field names matched to each page's actual row shape). `JobRow.title` (Task 4) and
`Job.title` (Task 6) are two distinct types for two distinct query shapes (child vs. teacher
surfaces), both `string | null` — matches the backend plan's `jobs.title text` (nullable, Task 3
of the backend plan).
