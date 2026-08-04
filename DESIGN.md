# StoryBuddy Design System

StoryBuddy uses the **Cobalt Playroom** visual direction: a bright creative-tool identity on top of a calm, book-like reading surface. This document is the canonical reference for product and marketing UI.

## 1. Design principles

1. **Imagination first.** The child’s words and finished story remain more prominent than controls or system status.
2. **Bold entry, calm reading.** Cobalt creates a memorable first impression. Ivory and soft surfaces support writing and reading.
3. **Playful, not noisy.** Use strong shape, scale, and illustration before adding more colors or decoration.
4. **Friendly clarity.** Labels are direct, recovery choices are visible, and technical pipeline language stays out of child-facing UI.
5. **Mobile first.** Every layout starts as one column and earns additional columns only when space allows.
6. **Accessible by default.** Preserve keyboard access, visible focus, readable contrast, reduced motion, and 44px minimum touch targets.

## 2. Theme

StoryBuddy is **light-first**. The default experience does not change automatically with `prefers-color-scheme`.

The physical scene is a child or adult writing, reviewing, or reading a picture book in a normally lit home or classroom. An ivory canvas reduces glare while keeping illustrations and controls bright.

Dark mode is not part of the current visual system. Add it only as a separately designed and tested feature, not as an automatic token inversion.

## 3. Color system

Use semantic CSS variables from `frontend/app/globals.css`. Do not hardcode brand colors in reusable product components.

### Brand foundation

| Role | Token | Value | Use |
|---|---|---:|---|
| Canvas | `--background` | `#F8F4E9` | Page background and reading space |
| Surface | `--color-surface` | `#FFFDF7` | Cards, story pages, inputs, raised panels |
| Muted surface | `--color-muted` | `#E9E3D7` | Dividers, disabled fills, quiet grouping |
| Ink | `--foreground` | `#18204A` | Primary text and icons |
| Cobalt | `--color-primary` | `#3155D9` | Brand fields, primary product actions, links |
| Deep cobalt | `--color-primary-deep` | `#213C9A` | Pressed ledges and deep brand detail |
| Sun yellow | `--color-secondary` | `#F2C85F` | Primary CTA on cobalt, focus indication |
| Coral | `--color-coral` | `#EC6A51` | Illustration detail only |

### Color rules

- Cobalt is the committed brand color and may occupy a large surface such as a hero or final CTA section.
- Ivory is the default writing and reading canvas.
- Sun yellow is the high-attention action color on cobalt. Pair it with navy ink.
- Coral does not compete with actions. Keep it inside illustrations or rare decorative moments.
- A screen should not display every available color simply because the tokens exist.
- Never use pure black or pure white for primary surfaces.
- Verify WCAG AA contrast when introducing a new pairing. Do not infer contrast from visual similarity.

### Product-state colors

These colors communicate state and are not part of decorative brand composition.

| State | Token | Value | Text token |
|---|---|---:|---|
| Success | `--color-success` | `#36785A` | `--on-success` |
| Warning | `--color-warning` | `#D69520` | `--on-warning` |
| Destructive | `--color-destructive` | `#C5485C` | `--on-destructive` |
| Information | `--color-info` | `#3B6BC4` | `--on-info` |
| Adult or admin context | `--color-admin` | `#7047A3` | `--on-admin` |

Use state color only when the state is real. Do not expose moderation categories or machine errors to children.

## 4. Typography

StoryBuddy has two primary voices.

### Primary fonts

- **Outfit** (`--font-display`): wordmark, H1-H3, major labels, and short high-emphasis text.
- **Nunito** (`--font-kid`): child-facing body copy, story text, captions, buttons, and form guidance.

### Restricted utility fonts

- **Inter** (`--font-sans`): compact adult-facing forms and dense classroom or administrative UI only.
- **JetBrains Mono** (`--font-mono`): diagnostics, identifiers, and machine-readable values only. Never use it as marketing decoration.

### Type guidance

| Role | Mobile | Desktop | Line height |
|---|---:|---:|---:|
| Landing hero | `48px` | `72-88px` | `0.95-1.0` |
| Page H1 | `36px` | `48px` | `1.05` |
| Section H2 | `32px` | `48px` | `1.05-1.15` |
| Card H3 | `22px` | `28px` | `1.2` |
| Child body | `18px` | `18-20px` | `1.6` |
| Adult body | `14-16px` | `14-16px` | `1.5` |

- Use tight tracking only on large Outfit headings.
- Keep body lines under `65ch`; story text should stay under `60ch`.
- Hero headlines should fit within two lines on desktop.
- Avoid uppercase body copy. Short kickers may use uppercase with restrained tracking.

## 5. Layout and spacing

### Container

- Maximum content width: `1280px` (`max-w-7xl`).
- Mobile gutter: `20px`.
- Large phone and tablet gutter: `32px`.
- Desktop gutter: `48px`.
- Use full-width color fields only when color is carrying narrative structure.

### Responsive breakpoints

Follow Tailwind’s mobile-first breakpoints.

| Range | Expected behavior |
|---|---|
| Below `640px` | One column, full-width actions when useful, simplified decoration |
| `640-767px` | One column with wider gutters and occasional inline actions |
| `768-1023px` | Two-column compositions may begin if both columns remain readable |
| `1024px+` | Full split heroes, larger type, and asymmetric content grids |

Every multi-column component must define its own mobile collapse. Do not depend on accidental wrapping.

### Spacing rhythm

Use the 4px base scale, but do not apply identical padding to every section.

- Control gaps: `8-16px`.
- Component padding: `16-32px`.
- Section spacing on mobile: `64-80px`.
- Section spacing on desktop: `96-128px`.
- Keep closely related heading and body copy visually grouped.

## 6. Shape, borders, and elevation

Cobalt Playroom is soft and tactile, not hard neo-brutalist.

### Radius

| Element | Radius |
|---|---:|
| Buttons and inputs | `12-16px` |
| Cards and story frames | `16-24px` |
| Large feature panels | `24px` |
| Avatars and true circular controls | `9999px` |

Pills are for tags or compact status only. Do not turn every control into a pill.

### Borders

- Default border: `1px` using cobalt at roughly 15-24% opacity.
- Dividers may use the same tint at lower emphasis.
- Avoid thick black outlines and colored side stripes.

### Shadows

Use soft cobalt-tinted shadows to communicate elevation.

- Small: `0 6px 18px rgb(49 85 217 / 10%)`.
- Medium: `0 10px 28px rgb(49 85 217 / 12%)`.
- Large: `0 22px 60px rgb(49 85 217 / 16%)`.

Do not use pure black shadows, decorative glow, or elevation on every container. Existing `.neo-*` utility names are compatibility aliases and now resolve to this softer treatment.

## 7. Buttons and interaction

### Action hierarchy

- **Primary on ivory:** cobalt background with surface-colored text.
- **Primary on cobalt:** sun-yellow background with navy text.
- **Secondary:** text link or quiet outlined control. Do not create a second competing filled action.
- Use one label for each action intent. Do not mix “Start,” “Begin,” and “Create” for the same destination on one screen.

### States

- Minimum interactive target: `44x44px`.
- Hover: lift by no more than `2px`; do not change semantic hue.
- Active: return toward the surface and reduce the shadow.
- Focus: `3px` sun-yellow outline with `3px` offset.
- Disabled: lower contrast, remove lift, use `not-allowed`, and retain a readable label.
- CTA labels remain on one line on desktop.

## 8. Motion

Motion communicates feedback or state change. It is not ambient decoration.

| Token | Value | Use |
|---|---:|---|
| `--duration-micro` | `150ms` | Press and hover feedback |
| `--duration-normal` | `250ms` | Small state transitions |
| `--duration-slow` | `400ms` | Major step transitions |
| `--duration-loading` | `1200ms` | Progress pulse or shimmer |

Use exponential ease-out for entrances and direct feedback. Avoid bounce, elastic easing, parallax, scroll hijacking, and perpetual decorative motion.

Under `prefers-reduced-motion: reduce`, remove repeating animation and reduce transitions to effectively instant feedback.

## 9. Imagery and illustration

Illustration is the main source of visual variety.

- Favor open books, page stacks, paper layers, and child-authored worlds.
- Use cobalt, yellow, green, and coral inside artwork without turning controls into a rainbow.
- Generated story images must remain the hero in reader and reveal screens.
- Decorative visuals use `aria-hidden="true"`. Informative images require concise, specific alt text.
- Reserve image space to prevent layout shift.
- Do not use generic fake dashboards, stock child photography, or decorative mascot clutter.

## 10. Landing-page composition

The canonical landing-page sequence is:

1. Compact cobalt navigation with one action.
2. Split cobalt and ivory hero with copy first in the DOM.
3. Open storybook hero visual on the ivory side.
4. A concise creation sequence: write, preview, read.
5. One large character-continuity story.
6. Calm child-friendly safety reassurance.
7. Final cobalt CTA and compact footer.

Below `1024px`, the hero stays stacked: cobalt copy followed by an ivory book stage. At `lg` and above, it becomes the split composition. The CTA stays visible before the decorative visual, and no horizontal scrolling is allowed.

## 11. Product states

### Loading

- Match the final content shape to prevent layout shift.
- Use a quiet pulse or shimmer only while progress is real.
- Pair progress visuals with plain language about what is happening.

### Errors and recovery

- Use the same visual quality as success screens.
- Explain what the child can do next: revise, redraw, or retry.
- Never show raw `jobs.error`, moderation categories, provider names, or stack traces.
- Error messages use `role="alert"` or an appropriate live region.

### Empty states

- State what is missing.
- Provide one clear recovery action.
- Use illustration only when it supports comprehension.

## 12. Accessibility checklist

Before shipping a UI change, verify:

- Body text and controls meet WCAG AA contrast.
- Keyboard focus is always visible.
- Touch targets are at least `44x44px`.
- Heading levels follow document order.
- Decorative art is hidden from assistive technology.
- Informative imagery has meaningful alt text.
- Layout works at `320px` without horizontal overflow.
- Text remains usable at 200% zoom.
- Reduced-motion behavior has been tested.
- Loading and dynamic errors use appropriate live regions.

## 13. Explicit non-goals

The following are not part of Cobalt Playroom:

- Automatic dark mode.
- Thick black neo-brutalist borders and flat black shadows.
- Bubblegum pink and electric cyan as competing brand actions.
- Rainbow color use on a single screen.
- Comic halftones, speech bubbles, starburst badges, or “BOOM” decoration.
- Confetti as a default success treatment.
- Glassmorphism, neon glow, gradient text, and AI-purple effects.
- Decorative monospace labels, section numbering, and repeated eyebrow text.
- Identical three-card feature grids when spacing or a structured sequence is clearer.

When adding a new pattern, extend this system rather than creating a parallel theme.
