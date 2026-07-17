# StoryBuddy — Mobile UX & Responsive Guidelines

This document synthesizes the UI/UX intelligence with StoryBuddy's specific product requirements (PRD v2) and design language (`DESIGN.md`) to establish strict rules for building the responsive web application.

---

## 1. Dual-Audience Responsive Strategy
StoryBuddy serves two distinct user groups with conflicting UI needs. The responsive design must enforce this divergence on mobile devices:

### A. Kid Workspace (Cartoon-Pop)
- **Goal:** Immersive, forgiving, playful, and oversized.
- **Touch Targets (CRITICAL):** Minimum `44x44px` for all interactive elements. Strongly prefer larger (`64px` - `80px`) for primary actions like "GO" or "Generate".
- **Density:** Low. One primary action per screen. Avoid visual clutter.
- **Scrolling:** Vertical only. **Never allow horizontal scrolling** in the main story flow.
- **Forms:** Giant handwriting-style textboxes. Validation only on submit or blur, never on keystroke.

### B. Teacher Dashboard (Neo-Brutalist Control Room)
- **Goal:** High density, observability, and efficiency.
- **Touch Targets:** Standard `44x44px` minimum, but packed more closely using the `8px` spacing scale.
- **Density:** High. Data tables appear at `md` (768px). Below `md` (mobile), tables MUST collapse into stacked cards or accordions.

---

## 2. Navigation Patterns by Breakpoint

Navigation structures physically morph across breakpoints to match device ergonomics.

| Viewport | Breakpoint | Kid Flow Navigation | Teacher Flow Navigation |
| :--- | :--- | :--- | :--- |
| **Mobile** | `xs`, `sm` (< 768px) | **Bottom Tab Bar** (Max 3 items, icon + text) | **Top Bar + Bottom Sheet Drawer** |
| **Tablet** | `md` (768px - 1023px)| **Top Navbar** (chunky) | **Collapsible Sidebar** |
| **Desktop**| `lg`, `xl` (≥ 1024px) | **Top Navbar** (chunky) | **Persistent Sidebar** |

**Mobile Navigation Rules:**
- **No mixed patterns:** Don't use a Hamburger Menu + Bottom Nav for kids. Stick to the Bottom Tab Bar.
- **Bottom Sheets:** Use `rounded-t-3xl` for modals and sheets to keep the friendly, tactile feel. Always include a swipe-down affordance (pull indicator).

---

## 3. Typography & Spacing on Mobile

### Typography
- **Kids (Nunito):** Mobile Base `18px` (Prevents iOS auto-zoom on inputs). Maximize legibility.
- **Teachers (Inter):** Mobile Base `14px`. Use `16px` specifically for `<input>` elements to prevent iOS zoom.
- **Line Length:** Cap at `60ch` on tablet/desktop. On mobile, ensure generous side margins (`16px` gutter).

### Spacing & Layout
- **Gutter Padding:** Use `16px` on mobile (`xs`, `sm`), `24px` on tablet (`md`), and `32px` on desktop (`lg+`).
- **Incremental Spacing:** Strictly use Tailwind's `4px/8px` system (`p-2`, `p-4`, `gap-4`).

---

## 4. Interaction, Feedback & States

On mobile, tactile feedback is paramount.

- **Tap Feedback:**
  - *Kid Flow:* Use spring physics. Buttons "depress" entirely (shadow drops to `0px`, translates `4px` down/right). 
  - *Wait States:* If an action takes >300ms, immediately show a diegetic Lottie animation (e.g., spinning pencil) inside the button or as a full-page skeleton. Never leave a frozen screen.
- **Gestures:**
  - Support system back gestures (iOS swipe back).
  - Use `touch-action: manipulation` on buttons to remove the 300ms tap delay.
- **Modals/Sheets:** Modals must not block the entire screen without a clear escape route. Prefer Bottom Sheets over centered modals for mobile ergonomics.
- **Errors:** 
  - Use Comic Red (`#EF476F`) with Ink Black text.
  - Present errors as friendly setbacks ("Oops! The story machine needs a break") with a clear, oversized retry button.

---

## 5. Accessibility & Performance (Mobile-First)

- **Contrast:** Ensure all text-on-background pairs meet 4.5:1. Use Ink Black (`#09090B`) text on brightly colored buttons (like Bubblegum Pink or Sunburst Yellow).
- **Reduced Motion:** Respect `prefers-reduced-motion` media queries. Replace bouncy spring animations with simple crossfades/opacity shifts.
- **Viewport Meta:** Ensure `width=device-width, initial-scale=1, maximum-scale=1` (only if input fonts are ≥16px) to prevent layout thrashing and accidental zooming during enthusiastic tapping.
- **Image Optimization:** Storybook images must be responsive. Use `aspect-ratio` to reserve space and prevent Cumulative Layout Shift (CLS) when generating the book pages.
