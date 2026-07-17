# StoryBuddy — User Flow & UX Decisions

This document outlines the step-by-step user flow, interaction patterns, and UX decisions for both the Student (Primary) and Teacher (Gatekeeper) experiences. It heavily emphasizes a **Mobile-First Design Strategy**, specifying layout components, navigation paradigms, and responsive behaviors.

---

## 1. Roles & Perspectives

- **Teacher (Gatekeeper):** Manages the classroom, creates student profiles, and acts as the moderation backstop. Requires a high-density, structured, and informative interface.
- **Student (Author):** The primary user (Grade 5-6). Needs a playful, forgiving, and guided experience with large touch targets, minimal text, and high structural clarity. No direct signup or PII entry.

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
  - **Data Display:** Dense data tables (`shadcn/ui` style) for efficient batch approvals.

### Student Layout Pattern
- **Mobile (< 768px):**
  - **Navigation:** **Bottom Tab Bar** (Home, Bookshelf, Gallery). Limit to 3 items. Text labels must accompany icons.
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
   - Teacher signs up / logs in via Supabase Auth.
   - Lands on **Teacher Dashboard** (Grid of classroom cards).
2. **Classroom Creation:**
   - Clicks "Create Classroom". (Opens a **Bottom Sheet** on mobile, **Dialog** on desktop). Enters a name.
3. **Student Profile Setup:**
   - Teacher adds students manually.
   - Desktop: Inline table row addition. Mobile: **Bottom Sheet** form.
   - Generates a unique, simple login code/link for each student.
4. **Story Library & Review:**
   - Badges indicate status: "Needs Review" (Warning Yellow), "Approved" (Mint Lime).
   - Teacher clicks a story to read it (opens a **Full-Screen Overlay**).
   - Toggles "Approved for Gallery" via a large Switch component.

---

## 4. Student Flow: Story Creation (The Core Loop)

1. **Login:**
   - Student enters their unique code in a large, auto-advancing segmented input field.
2. **Dashboard (Bookshelf):**
   - Student sees their past stories as 3D book covers (horizontal scrolling carousel on mobile, grid on desktop).
   - Giant primary CTA: **"Write a New Story!"** (Fixed at the bottom of the screen on mobile for easy thumb reach).
3. **The Editor (Distraction-Free Mode):**
   - **Interface:** The navigation bar hides. A large text area takes up 80% of the screen.
   - **Assistive UX:** Live word count / progress bar against the 500-word limit fixed directly above the keyboard.
   - **Action:** Floating Action Button (FAB) or sticky bottom button to "Create Picture Book".
4. **Input Gate & Loading (Crucial UX):**
   - **Wait State:** Screen transitions to a full-screen loading state: "Reading your story..." with a looping Lottie animation (e.g., book pages flipping).
   - *If Over-length:* A **Bottom Sheet** slides up gently interrupting: "Whoa, that's a long adventure! Let's make a book out of the first part." (Requires confirmation).
   - *If Moderation Fails:* Error state with a confused mascot. "Oops! The story machine didn't quite get that. Let's try changing a few words."
5. **Style & Character Reveal:**
   - Student selects from 3 **Style Presets** presented as large, tappable image cards.
   - The system reveals the generated **Canonical Character Reference**.
6. **Full Generation Wait State:**
   - "Drawing your scenes..." 
   - Uses a staggered vertical stepper to show progress (Scene 1 done... Scene 2 drawing...) synced with Supabase Realtime.
7. **The Storybook Slideshow (Final Output):**
   - Immersive, full-screen reader. Landscape orientation is forced or highly encouraged on mobile.
   - **Layout:** Image on top/left, verbatim text caption below/right.
   - **Controls:** Giant Next/Prev tap zones (left 30% and right 30% of screen). Play button for **expressive TTS narration** (Chatterbox; ADR-020).
8. **The Story Map:**
   - A summary screen after reading: "You created 3 characters, 2 places, and 5 scenes!" 

---

## 5. Student Flow: Peer Reflection

1. **Classroom Gallery:**
   - Browse stories written by classmates via a vertical feed of large cards (Mobile) or masonry grid (Desktop).
2. **Reflection Prompt:**
   - At the end of a book, a **Bottom Sheet** slides up with fixed reflection prompts.
   - Example: "What was your favorite part?" (Textarea grows as they type).
3. **Submission:**
   - Routed through the input moderation gate.
   - The author receives this reflection on their Story Map.

---

## 6. Error States & Fallbacks

- **Pipeline Stalls/Timeout:** If LangGraph stalls, the system saves the checkpoint. The full-screen spinner transitions to a friendly illustration: "Taking a little longer... We saved your progress! You can leave and come back."
- **Image Generation Self-Refusal:** If the model refuses a prompt, the system automatically retries with a softened prompt behind the scenes. If it repeatedly fails, the scene is skipped with a friendly placeholder card: "This scene was too wild to draw!"
- **VLM Consistency Failure:** Triggers a background regeneration. The user just sees the loading step taking slightly longer; the complexity is completely hidden.
