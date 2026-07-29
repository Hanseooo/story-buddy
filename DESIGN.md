# StoryBuddy — Design & Theme Bible

This document acts as the high-level visual, structural, and behavioral reference for styling the **StoryBuddy** application.

---

## 🎨 Visual Identity: Cartoon-Pop meets Neo-Brutalist
The interface blends the high-energy, expressive vibes of childhood cartoons with the structured, high-contrast clarity of modern neo-brutalism. This creates an environment that feels both like a playground and a highly responsive tool.

### 1. Color Strategy (Restrained but Punchy)
We use warm, tinted pastels for all structural canvases to act as a neutral background, but reserve High-Chroma colors exclusively for primary calls-to-action. The generated story remains the hero.

**Surface & Background Layers**
*   **Page Background Canvas:** `#FAF6EE` (Warm, tinted pastel cream). Prevents eye strain compared to pure white.
*   **Foreground Card/Surface:** `#FFFFFF` (Pure White). Clearly lifts cards off the cream canvas — the warm surrounding context makes white read warm, not cold.

**Semantic Palette & Accessibility Pairings**
*(Rule: Never guess text colors. Always use the specified "On-[Color]" pairing to guarantee WCAG 4.5:1 contrast).*
*   **Primary Action (Bubblegum Pink):** `#FF6B9E` | *Text:* `#09090B` (Ink Black)
*   **Secondary Action (Electric Cyan):** `#06BEE1` | *Text:* `#09090B` (Ink Black)
*   **Warning/Alert (Sunburst Yellow):** `#FFD166` | *Text:* `#09090B` (Ink Black)
*   **Success (Mint Lime):** `#06D6A0` | *Text:* `#09090B` (Ink Black)
*   **Error/Destructive (Comic Red):** `#EF476F` | *Text:* `#09090B` (Ink Black)
*   **Info/Advisory (Sky Blue):** `#4A90D9` | *Text:* `#09090B` (Ink Black). Neutral callouts, advisory banners, tooltips — intent-neutral so it doesn't collide with Secondary Cyan.
*   **Parental/Admin (Royal Violet):** `#8338EC` | *Text:* `#FFFFFF` (White)
*   **Ink Black (True Black):** `#09090B` | *Text:* `#FFFFFF` (White). Used for thick solid outlines, heavy drop shadows, and primary text.

*   **Color Consistency Lock:** Despite having a full 6-color palette, **pick 1-2 primary accents per screen or flow** and stick to them. Do not fluctuate wildly within a single view just because all colors exist.

**Dark Mode ("Comfort Cosmic Night")**
*   **Page Background Canvas:** `#12121A` (Softer deep indigo). Lifted from pure black to reduce halation and astigmatism strain.
*   **Foreground Card/Surface:** `#1C1C26` (Slightly lighter indigo for panels).
*   **Text/Foreground:** `#E4E4E7` (Soft slate/zinc). Reduces the harsh glow of pure white text.
*   **Accents & Semantic Colors (exact dark mode values):** Both saturation (~10%) and lightness (~8%) are reduced to prevent neon fatigue without losing color identity. Use these values exactly — do not interpolate at runtime:

    | Semantic | Dark Mode Hex |
    |----------|---------------|
    | Primary (Pink) | `#E8547F` |
    | Secondary (Cyan) | `#05A0C8` |
    | Warning (Yellow) | `#EFC050` |
    | Success (Mint) | `#05C090` |
    | Error (Red) | `#DC3B60` |
    | Info (Sky Blue) | `#3A7EC4` |
    | Parental/Admin (Violet) | `#7228D8` |

    ⚠️ **Dark mode usage rule:** Semantic colors on dark backgrounds are for interactive elements and status indicators only — buttons, badges, toast borders, icons. Never use them as large panel or page fills — the luminance contrast against `#12121A` would cause glare at scale.

*   **Borders & Shadows (Ink):** `var(--color-ink)` resolves to `#3C3C54` in dark mode — a neutral indigo-grey visibly lighter than the `#1C1C26` card surface, creating a hard offset ledge without neon glow.

*(Accessibility Rule: Text on any background must maintain a contrast ratio of at least 4.5:1. Use Ink Black on brightly colored buttons if white fails contrast checks.)*

### 2. Typography Pairings & Scales (Upgraded)
To maximize both emotional playfulness for kids and high technical readability for parents/educators, we use a divergent typography system:

*   **Display / Headings (Global):** `"Outfit"`. Modern, friendly, and geometric. Used for all H1-H3.
*   **Kid Workspace Body (Primary):** `"Nunito"`. With its rounded terminals and balanced proportions, Nunito is exceptionally friendly and highly legible for early-to-mid readers (Grade 5-6).
    *   *Scale:* Mobile Base `18px`, Desktop Base `20px` (Extremely large for readability). Line height: `1.6`.
*   **Teacher Dashboard Body (Secondary):** `"Inter"`. Highly functional and crisp. Perfect for data tables, settings, and dense UI.
    *   *Scale:* Mobile Base `14px`, Desktop Base `14px`. Line height: `1.5`.
*   **Data, Stats, Console, PII Logs:** `"JetBrains Mono"` for diagnostic outputs, model scores, and server log sequences.

### 3. Key Layout & Neo-Brutalist Utility Accents
*   **Spacing Scale:** Stick strictly to a 4px/8px incremental spacing scale. Maintain at least `8px` gap between interactive elements.
*   **Thick Borders:** `.neo-border` applies `border: 3px solid var(--color-ink)`.
*   **Flat Shadows:** `.neo-shadow` applies `box-shadow: 4px 4px 0px 0px var(--color-ink)`. *(Note: Standard UX rules forbid pure black drop shadows on light backgrounds, but this `var(--color-ink)` shadow is the deliberate stylistic anchor of our Neo-Brutalist theme).*
*   **Soft Rounded Corners:** Generous rounding (`rounded-xl` to `rounded-3xl`) keeps the UI friendly.
*   **Z-Index Scale:** 0 (base) / 10 (sticky nav) / 20 (overlays) / 40 (bottom sheets/modals) / 100 (toasts).
*   **Touch Targets (Critical):** All interactive elements in the Kid Workspace MUST have a minimum size of `44x44px`.

### 3.5 Animation Token System

We define explicit animation tokens to enforce consistent motion behavior across the app.

**Durations**
| Token | Value | Use |
|-------|-------|-----|
| `--duration-micro` | `150ms` | Button press, toggle, checkbox, tooltip |
| `--duration-normal` | `250ms` | Panel expand, bottom sheet slide, card hover |
| `--duration-slow` | `400ms` | Page transition, wizard step change, stepper advance |
| `--duration-loading` | `1200ms` | Lottie loop cycle, skeleton shimmer sweep |

**Easing Curves**
| Token | Value | Use |
|-------|-------|-----|
| `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Enter animations — bouncy, playful overshoot |
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | Exit animations — natural deceleration |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | Symmetric transitions — crossfades, looping |

**Motion Rules**
*   Exit animations use 60–70% of enter duration (exit feels snappier).
*   Stagger list/grid item entrances by `40ms` per item.
*   Maximum 2 animated elements per viewport simultaneously.
*   Forward navigation animates left/up; backward animates right/down.

**`prefers-reduced-motion` Behavior:**
*   Replace `--ease-spring` with `--ease-out` (no overshoot).
*   Cap all durations at `150ms` — never instant (instant feels broken).
*   Disable Lottie animation loops; show static first frame.
*   Replace slide/scale transitions with crossfade (opacity only).
*   Keep simple opacity fades — these are universally safe.

### 3.6 Elevation Scale (Flat Shadow)

All shadows use the flat, unblurred Neo-Brutalist shadow style. This scale governs which component type gets which shadow level.

| Level | CSS | Use For |
|-------|-----|---------|  
| 0 | `none` | Flat inline elements, disabled states |
| xs | `1px 1px 0px 0px var(--color-ink)` | Tags, badges, pills |
| sm | `2px 2px 0px 0px var(--color-ink)` | Inline cards, secondary buttons |
| md | `4px 4px 0px 0px var(--color-ink)` | Elevated cards, primary buttons |
| lg | `6px 6px 0px 0px var(--color-ink)` | Bottom sheets, modals, floating panels |
| xl | `8px 8px 0px 0px var(--color-ink)` | Hero cards, storybook cover, feature highlights |

*   **Hover:** Increase one level (e.g., md → lg) with a `translate(-2px, -2px)` lift.
*   **Active/Pressed:** Drop to level 0 with `translate(4px, 4px)` (button "depresses").
*   **Dark mode:** Same sizes; `var(--color-ink)` resolves to `#3C3C54` (neutral indigo-grey ledge, not neon).

### 3.7 Border Radius by Context

Radius is not uniform — kid-facing elements are rounder and friendlier, teacher-facing elements are tighter and more functional.

| Context | Radius | Tailwind Class |
|---------|--------|----------------|
| Kid buttons / primary CTAs | `16px` | `rounded-2xl` |
| Kid cards / story panels | `24px` | `rounded-3xl` |
| Teacher form inputs | `8px` | `rounded-lg` |
| Teacher cards / data panels | `12px` | `rounded-xl` |
| Avatars / thumbnails | `9999px` | `rounded-full` |
| Tags / badges / pills | `9999px` | `rounded-full` |
| Bottom sheets (top only) | `24px` top | `rounded-t-3xl` |
| Storybook pages | `16px` | `rounded-2xl` |

### 3.8 Responsive Breakpoints & Container Strategy

Mobile-first. Styles default to the smallest breakpoint, then scale up.

| Breakpoint | Width | Container | Gutter | Kid Nav | Teacher Nav |
|------------|-------|-----------|--------|---------|-------------|
| xs (phone) | `0–639px` | Full width | `16px` | Bottom Tab Bar (3 items) | Top Bar + Bottom Sheet drawer |
| sm (large phone) | `640–767px` | Full width | `16px` | Same as xs | Same as xs |
| md (tablet) | `768–1023px` | Full width | `24px` | Top Navbar | Collapsible Sidebar |
| lg (desktop) | `1024–1439px` | `max-w-6xl` | `32px` | Top Navbar | Persistent Sidebar |
| xl (wide) | `1440px+` | `max-w-7xl` | `32px` | Same as lg | Same as lg |

**Content line length:** Kid body text capped at `60ch` on desktop for readability. Teacher data tables appear at `md+`; below `md`, use accordions or stacked cards.

### 3.9 Font Usage Map

Which font is used where — preventing accidental use of the wrong typeface.

| Context | Font | Variable | Mobile Size | Desktop Size | Line Height |
|---------|------|----------|-------------|--------------|-------------|
| H1 (page title) | Outfit | `--font-display` | `28px` | `48px` | `1.1` |
| H2 (section heading) | Outfit | `--font-display` | `22px` | `36px` | `1.2` |
| H3 (subsection / card title) | Outfit | `--font-display` | `18px` | `28px` | `1.3` |
| Kid body text, story editor, captions | Nunito | `--font-kid` | `18px` | `20px` | `1.6` |
| Teacher body text, dashboard, forms | Inter | `--font-sans` | `14px` | `14px` | `1.5` |
| Data, stats, logs, console output | JetBrains Mono | `--font-mono` | `13px` | `13px` | `1.5` |

*Note: Outfit is used for H1–H3 across both kid and teacher contexts. Teacher dashboard headings use the same Outfit scale — Inter is body/form copy only.*

### 4. Layout Discipline (Anti-Slop)
*   **CTA Wrap Ban:** Button text MUST fit on one line at desktop. Max 3 words (e.g., "Generate Story"). Wrapped CTAs at desktop are broken design.
*   **No Duplicate CTA Intent:** Do not have two CTAs with the same intent on one page (e.g., "Start Story" and "Begin Story"). Pick one label and lock it.
*   **Bento Grid Discipline (Teacher Dashboard):** Bento grids must have exactly as many cells as content (never leave an empty cell). At least 2-3 cells in any grid need background diversity (a pattern, image, or tinted background)—not just white cards on a white canvas.
*   **Eyebrow Restraint:** Avoid the AI default of adding small uppercase tracking text (`EYEBROW`) above every section headline. Maximum 1 eyebrow per 3 sections.

### 5. Interactive States & Micro-behaviors
*   **Hover:** Flat-shadow buttons translate slightly (`translate-x-[-2px] translate-y-[-2px]`) while the shadow expands to `6px 6px`. **Color does not change on hover** — transform is the sole signal. Hue shifts on hover would dilute the semantic meaning of the palette.
*   **Active (Click):** Button depresses completely (`translate-x-[4px] translate-y-[4px]`) and the shadow reduces to `0px`. Color stays the same.
*   **Focus (A11y):** Visible focus rings are mandatory. Use a `4px` outline in Sunburst Yellow (`#FFD166`) offset by `2px` for keyboard navigation. Yellow is used (not Cyan) because Cyan is already the Secondary action color — a focused Secondary button would be indistinguishable from its rest state.
*   **Disabled:** Reduce opacity to `0.5`, remove the drop shadow, change cursor to `not-allowed`.
*   **Motion & Easing:** Use spring physics for interactions rather than linear easing, but keep durations snappy (`150ms–300ms`). Respect `prefers-reduced-motion` to disable bouncy animations.

---

## 📐 Divergent Register Scaling (Layout Hierarchy)
We do not use one responsive sizing rule for the whole app. The scaling diverges based on the user:

*   **Kid Workspace (Saturated & Chunky):** Must remain radically oversized everywhere. Even on a 4K desktop monitor, a giant 80px "GO" button feels satisfying. Massive touch targets (`44x44px` minimum), playful starter prompt capsules, a giant handwriting-style textbox. Avoid horizontal scrolling.
*   **Teacher / Researcher Center (Structured & Clean):** Must instantly snap to high-density, technical observability scaling (`text-sm`, `Inter`, `JetBrains Mono`, compact tables, breadcrumb navigation). The contrast reinforces that one is a playground and the other is a control room.

---

## ⚡ Form, Feedback, & States
To ensure the app feels alive, highly responsive, and forgiving:

*   **Loading States (Spatial Skeletons + Micro-Narrative):** 
    *   Skeletons must match the exact shape of incoming content to reserve space and prevent layout shift (CLS).
    *   **Skeleton colors:** Light mode — base `#EDE8DF`, shimmer sweep `#F5F1E8`. Dark mode — base `#242430`, shimmer sweep `#2E2E3E`. The shimmer is a CSS `linear-gradient` animation running on `--duration-loading` (`1200ms`).
    *   Inside the flat-color skeleton block, inject a small, looping diegetic animation (e.g., a cartoon pencil scribbling or a wand spinning) to hold the space technically while entertaining narratively.
    *   Buttons should show an internal spinner and disable themselves when submitting.
*   **Success States (Toasts & Confetti):**
    *   **Toasts:** Slide up from the bottom center, styled as mini comic panels (`.neo-border`, `.neo-shadow`) with a distinct Mint Lime left-border. Auto-dismiss in 4 seconds. Provide aria-live regions.
    *   **Micro-animations:** Subtle starburst or confetti particle bursts on primary goal completions.
*   **Error States (Friendly & Actionable):**
    *   Errors should never feel punishing. Use Comic Red panels with a gentle, confused mascot icon.
    *   Provide clear, jargon-free actionable steps (e.g., "Oops! The story machine needs a break. Let's try that again!").
    *   Inline form errors appear immediately below the input with a subtle horizontal shake animation. Validation should happen on blur or submit, not keystroke.
    *   **Accessibility (A11y):** Form errors MUST use `aria-live` regions or `role="alert"` to notify screen readers dynamically.
*   **Empty States & Progressive Disclosure:**
    *   Show a helpful message and illustration, but **always include a clear recovery path or primary action** (e.g., A sad pencil + a "Write your first story" button).
    *   **Progressive Disclosure:** For the Teacher Dashboard, reveal complex data progressively. Use accordions or "View Details" to avoid cognitive overload on the primary view.

---

## 📚 6. Comic-Book Theme Addendum (Toggleable & Reversible)
To make the interface even more immersive for older kids and teenagers, a **Comic Book / Graphic Novel Theme overlay** is available. This aesthetic applies **extreme contrast by region**:

*   **Heavy Structure, Clean Content:** The Ben-Day radial gradient dots (`.comic-halftone`) and double-thick borders go heavy on the structural panels, gutters, and navigation. However, the actual reading panels (the "balloons") remain stark, clean, and dot-free to ensure 100% accessibility for reading.
*   **Speech Bubble Captions:** Story captions style as clean dialog balloons with an upward-pointing speech tail (`.comic-bubble-tail-up`) and a solid black backing outline.
*   **Dynamic Action Badges:** Retro starburst badges (like `⚡ BOOM!` or `✨ NEW!`) overlay key hero components.
*   **Diegetic UI:** The "Write your story" input area is styled as a large lined notebook paper or a clean speech bubble, grounding the UI in the physical world of a comic.
*   **Comic Motion (Bursts):** When interacting with primary actions (like "Generate Story"), buttons use spring physics to depress deeply and trigger tiny SVG starburst background flashes instead of standard ripples.

---

## 🎭 7. Avatars & Student Profiles
To adhere strictly to PII/privacy requirements (preventing minors from uploading real photos) while maintaining a highly engaging, playful environment, we use **deterministic generative avatars**.

*   **Generative Engine:** We utilize deterministic SVG avatar generators (e.g., **DiceBear** API) using styles like `bottts`, `fun-emoji`, or `adventurer`.
*   **Determinism:** The avatar seed is tied to the student's nickname or profile ID so their character remains consistent across sessions.
*   **Loading States:** All avatars must render a circular `.shimmer` skeleton of the exact final dimensions (`rounded-full`) to prevent layout shift while the external SVG loads.
*   **Fallbacks:** If the generative service fails, the `onError` fallback is a flat, highly-saturated circle (from our semantic palette) displaying the first 1-2 initials of the student's nickname in Ink Black text.
