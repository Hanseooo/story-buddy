# StoryBuddy — Mobile UX & Responsive Guidelines

This document synthesizes the UI/UX intelligence with StoryBuddy's specific product requirements (PRD v2) and design language (`DESIGN.md`) to establish strict rules for building the responsive web application.

---

## 1. Dual-Audience Responsive Strategy
StoryBuddy serves two distinct user groups with differing UI needs under the unified **Cobalt Playroom** design system (`DESIGN.md`):

### A. Kid Workspace (Nunito / Playful)
- **Goal:** Immersive, forgiving, playful, and tactile reading/writing surface on an ivory canvas (`#F8F4E9`).
- **Touch Targets (CRITICAL):** Minimum `44x44px` for all interactive elements. Strongly prefer larger (`56px` - `64px`) for primary actions.
- **Density:** Low. One primary action per screen. Avoid visual clutter and mascot noise (`DESIGN.md §11`).
- **Scrolling:** Vertical only. **Never allow horizontal scrolling** in the main story flow.
- **Forms:** Large, friendly textboxes. Validation only on submit or blur, never on keystroke.

### B. Teacher Dashboard (Inter / Density)
- **Goal:** High density, observability, and efficiency for classroom management.
- **Touch Targets:** Standard `44x44px` minimum, organized using the `8px` spacing scale.
- **Density:** High. Data tables appear at `md` (768px). Below `md` (mobile), tables collapse into stacked cards or accordions.

---

## 2. Navigation Patterns by Breakpoint

Navigation structures physically morph across breakpoints to match device ergonomics.

| Viewport | Breakpoint | Kid Flow Navigation | Teacher Flow Navigation |
| :--- | :--- | :--- | :--- |
| **Mobile** | `xs`, `sm` (< 768px) | **Bottom Tab Bar** (Max 3 items, icon + text) | **Top Bar + Bottom Sheet Drawer** |
| **Tablet** | `md` (768px - 1023px)| **Top Navbar** | **Collapsible Sidebar** |
| **Desktop**| `lg`, `xl` (≥ 1024px) | **Top Navbar** | **Persistent Sidebar** |

**Mobile Navigation Rules:**
- **No mixed patterns:** Don't use a Hamburger Menu + Bottom Nav for kids. Stick to the Bottom Tab Bar (`StudentTabBar.tsx`).
- **Bottom Sheets / Dialogs:** Use `rounded-t-3xl` for modals and sheets to keep the friendly, tactile feel. Always include a swipe-down affordance (pull indicator).

---

## 3. Typography & Spacing on Mobile

### Typography
- **Kids (Nunito):** Mobile Base `18px` (Prevents iOS auto-zoom on inputs). Maximize legibility (`DESIGN.md §4`).
- **Teachers (Inter):** Mobile Base `14px`. Use `16px` specifically for `<input>` elements to prevent iOS zoom.
- **Line Length:** Cap at `60ch` on tablet/desktop. On mobile, ensure generous side margins (`16px` gutter).

### Spacing & Layout
- **Gutter Padding:** Use `20px` on mobile (`xs`, `sm`), `32px` on tablet (`md`), and `48px` on desktop (`lg+`) (`DESIGN.md §5`).
- **Incremental Spacing:** Strictly use Tailwind's `4px/8px` system (`p-2`, `p-4`, `gap-4`).

---

## 4. Interaction, Feedback & States

On mobile, tactile feedback is paramount.

- **Tap Feedback:**
  - *Kid Flow:* Buttons lift by ≤2px on hover and return toward the surface on active press (`DESIGN.md §7`).
  - *Wait States:* Use subtle shimmer/pulse skeletons matching content shapes (or the 4-step Realtime progress stepper). Never leave a frozen screen.
- **Gestures:**
  - Support system back gestures (iOS swipe back).
  - Use `touch-action: manipulation` on buttons to remove the 300ms tap delay.
- **Modals/Sheets:** Modals must not block the entire screen without a clear escape route. Prefer Bottom Sheets over centered modals for mobile ergonomics.
- **Errors:** 
  - Use semantic destructive tokens (`--color-destructive: #C5485C` with `--on-destructive: #FFFDF7`).
  - Present errors as friendly setbacks ("Oops! The story machine needs a break") with a clear retry button via `FailureScreen.tsx`.

---

## 5. Accessibility & Performance (Mobile-First)

- **Contrast:** Ensure all text-on-background pairs meet WCAG AA (4.5:1). Use semantic ink (`--foreground: #18204A`) on high-attention Sun Yellow (`--color-secondary: #F2C85F`) (`DESIGN.md §3`).
- **Reduced Motion:** Respect `prefers-reduced-motion` media queries (`globals.css`). Replace motion with opacity transitions.
- **Viewport Meta:** Ensure `width=device-width, initial-scale=1, maximum-scale=1` (with input fonts ≥16px) to prevent layout thrashing and accidental zooming.
- **Image Optimization:** Storybook images must be responsive. Use `aspect-ratio` to reserve space and prevent Cumulative Layout Shift (CLS) when loading story pages.
