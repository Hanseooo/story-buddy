# StoryBuddy — User Flow & UX Decisions

This document outlines the step-by-step user flow, interaction patterns, and UX decisions for both the Student (Primary) and Teacher (Gatekeeper) experiences. It heavily emphasizes a **Mobile-First Design Strategy**, specifying layout components, navigation paradigms, and responsive behaviors.

---

## 1. Roles & Perspectives

- **Teacher / BEED student (Account issuer + reviewer):** Manages the classroom, issues each student a
  classroom-scoped account (nickname + initial password), and is the manual human backstop — every
  generated book is approved or rejected by them before it reaches the gallery or export. Requires a
  high-density, structured, and informative interface.
- **Student (Author):** The primary user (Grade 5-6). Logs into their own teacher-issued account (classroom
  code + nickname + password) and authors their own story directly. Needs a playful, forgiving, and guided
  experience with large touch targets, minimal text, and high structural clarity. No self-serve signup, no
  email on the account.

---

## 2. Global Navigation & Layout Architecture (Mobile-First)

### Teacher Layout Pattern
- **Mobile (< 768px):** 
  - **Top App Bar:** Contains page title and an overflow hamburger menu.
  - **Navigation:** Use a **Bottom Sheet (Drawer)** for the mobile menu. It is much easier to reach one-handed than a standard sidebar.
  - **Data Display:** Use **Accordions** or stacked cards instead of data tables for student lists and story approvals.
- **Desktop (≥ 768px):** 
  - **Navigation:** Persistent **Left Sidebar** with clear routing (`Classrooms`, `Story Library`, `Settings`).
  - **Breadcrumbs:** Used in the top header (`Classrooms > Grade 5 > Story Library`) to provide deep context.
  - **Data Display:** Dense data tables and responsive cards (native HTML / Tailwind) for efficient batch approvals.

### Student Layout Pattern
- **Mobile (< 768px):**
  - **Navigation:** **Bottom Tab Bar** (Bookshelf, Gallery, Profile). Limit to 3 items. Text labels must accompany icons.
  - **Modals vs. Sheets:** NEVER use center-screen modals on mobile. Use **Bottom Sheets** (swipeable) for selections (e.g., picking a Style Preset) and confirmations. They are highly touch-friendly.
  - **Full-Screen Wizards:** Story creation must hide the Bottom Tab Bar to become a distraction-free, full-screen step-by-step wizard.
- **Desktop (≥ 768px):**
  - **Navigation:** Simple **Top Navbar** (Logo left, Navigation links center, Profile right).
  - **Modals:** Center-screen Dialogs are acceptable here for confirmations.

### Empty States
Whenever a table or list is empty, display a friendly placeholder:
- **Teacher Library:** "No stories generated yet. Invite students to write!" (Show in a dashed-border card).
- **Student Dashboard:** "Your bookshelf is empty! Let's write your first story." + Big Primary CTA.

---

## 3. Teacher Flow: Classroom Management

1. **Onboarding & Auth:**
   - Teacher or BEED student signs up / logs in via Supabase Auth.
   - Lands on **Classroom Picker** (Grid of classroom cards at `/classroom`).
2. **Classroom Creation:**
   - Clicks "Create Classroom". (Opens a **Bottom Sheet** on mobile, **Dialog** on desktop). Enters a name.
     A single classroom code is generated for sharing with students.
3. **Student Account Setup:**
   - Teacher adds each student: sets a nickname + an initial password (which the child can change later).
   - Desktop: Inline table row addition. Mobile: **Bottom Sheet** form.
   - Shares the classroom code with students (they combine it with their own nickname + password to log in).
4. **Story Library & Review:**
   - Badges indicate status: "Needs Review" (`--color-warning`), "Approved" (`--color-success`).
   - Teacher clicks a story to read it (opens a **Full-Screen Overlay** / `BookReviewDialog`).
   - Manually approves or rejects into the gallery via a large Switch component — every book is reviewed;
     there is no auto-approve mode (deferred to Future Work behind an ethics re-review).

---

## 4. Student Flow: Story Creation (The Core Loop)

1. **Login:**
   - Student enters the classroom code in a large, auto-advancing segmented input field.
   - Then enters their nickname + password (teacher-set; changeable from Settings). No email, no
     self-serve signup — this is a real login, not a profile pick.
2. **Dashboard (Bookshelf):**
   - Student sees their past stories as book covers (horizontal scrolling carousel on mobile, grid on desktop).
   - Giant primary CTA: **"Write a New Story!"** (Fixed at the bottom of the screen on mobile for easy thumb reach).
3. **The Editor (Distraction-Free Mode):**
   - **Interface:** The navigation bar hides. A large text area takes up 80% of the screen.
   - **Assistive UX:** Live word count / progress bar against the 500-word limit fixed directly above the keyboard.
   - **Action:** Sticky bottom button to "Create Picture Book".
4. **Input Gate & Loading (Crucial UX):**
   - **Wait State:** Screen transitions to a full-screen loading state: "Reading your story..." with subtle shimmer / pulse progress.
   - *If Over-length:* A **Bottom Sheet** slides up gently interrupting: "Whoa, that's a long adventure! Let's make a book out of the first part." (Requires confirmation).
   - *If Moderation Fails:* Friendly failure stage via `FailureScreen.tsx`: "Oops! The story machine didn't quite get that. Let's try changing a few words."
5. **Style & Character Reveal:**
   - Student selects from selectable **Style Presets** (`cel`, `gouache`, `cut_paper`; ADR-042) presented as large, tappable image cards.
   - The system reveals the generated **Canonical Character Reference**.
6. **Full Generation Wait State:**
   - "Drawing your scenes..." 
   - Uses a staggered vertical stepper to show progress (Scene 1 done... Scene 2 drawing...) synced with Supabase Realtime. The wait-state stepper is a four-step vertical list driven by `jobs.current_stage`. Step 3's label carries `k / N` when available.
7. **The Storybook Slideshow (Final Output):**
   - Immersive, full-screen reader. Orientation: no lock — portrait stacks image over caption via CSS media query. A device locked to portrait in system settings can always read the book.
   - **Layout:** Image on top/left, verbatim text caption below/right.
   - **Controls:** Giant Next/Prev tap zones (left 30% and right 30% of screen). Play button for **expressive TTS narration** (Chatterbox; ADR-020).
8. **Teacher review:** the book waits for manual teacher approval before it enters the classroom gallery
   or can be exported (§3.4).

---

## 5. Student Flow: Classroom Gallery

The child-facing Story Map is cut (ADR-021). The gallery is **display-only** — the approved storybook is
the only peer-visible artifact; there is no reflection, comment, or scoring surface of any kind.

1. **Classroom Gallery:**
   - Classmates browse and read approved books via a vertical feed of large cards (Mobile) or masonry
     grid (Desktop). Reading is the only peer interaction; there is no reply, comment, reflection, or
     scoring surface.

---

## 6. Error States & Fallbacks

- **Pipeline Stalls/Timeout:** If LangGraph stalls, the system saves the checkpoint. The full-screen spinner transitions to a friendly illustration: "Still going! We saved your spot, so you can leave and come back." The "Still going!" line appears after 90 seconds of no `current_stage` UPDATE.
- **Image Generation Self-Refusal:** If the model refuses a prompt, the system automatically retries with a softened prompt behind the scenes, then gently reframes ("let's imagine that part a little differently"). If it still fails, the **whole job** fails to a kid-appropriate failure screen — there is no placeholder page and no skipped scene, because a book is never delivered partial (ADR-010, ADR-025).
- **VLM Consistency Failure:** Triggers a background regeneration. The user just sees the loading step taking slightly longer; the complexity is completely hidden.

### 6.1 The three verbs

*(`docs/specs/kid-flow-failure-semantics.md`, 2026-08-02 — that spec is authoritative; this is the
index entry.)* The product used to call three different actions *"try again."* They are:

| Verb | Affects | Mechanism | New job? |
|---|---|---|---|
| **redraw** | one picture at the character reveal | `POST /jobs/{id}/confirm` `{action:"try_again"}` | no |
| **revise** | the child's words | child edits, then `POST /storybooks` | yes |
| **retry** | the run, text unchanged | `POST /storybooks` | yes |

`revise` is offered only when the failure was the child's own text. **Every other failure — and every
unrecognised one — offers `retry`, so the machine never blames the child.** The child is never shown
a moderation category, a flagged span, or the error string.

### 6.2 Terminal is not not-ready

Four render buckets, and every URL-reachable screen handles all four: **in-flight**
(`queued`/`running`) · **paused** (`awaiting_confirm`) · **terminal-success** (`complete` with pages)
· **terminal-failure** (`failed`, or a swept pause). A `failed` job must never render as a wait state.

A swept pause is **not** a failure and must not read to the child as their story breaking — same
`retry` action, gentler words. A complete book whose images will not sign re-signs in place; it never
rebuilds a whole book to repair an expired link.
