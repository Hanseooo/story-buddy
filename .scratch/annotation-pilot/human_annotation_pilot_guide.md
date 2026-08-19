Here is your step-by-step implementation plan for executing the Human Annotation Pilot and freezing the instrument.

### 1. Seed the 17 Pilot Pairs
First, we need to generate and upload the 17 meaningful visual pilot pairs to Supabase. The script will safely insert them into the `research_pairs` table and mark them as `is_pilot = true`.

**Run the following command:**
```bash
cd backend
uv run python -m scripts.pilot_annotate_seed
```
*Note: This will upload the images to the `private_assets` bucket using opaque paths and insert atomic records into the DB.*

### 2. Prepare the Research Accounts
You will need three separate user accounts to fulfill the roles.
1. Create 3 new accounts via the frontend (e.g., at `http://localhost:3000/login`).
2. Open your Supabase Dashboard (`http://127.0.0.1:54323` if local).
3. Navigate to the `profiles` table and assign the `researcher` role to all 3 accounts:
   ```sql
   UPDATE profiles SET role = 'researcher' WHERE id IN ('<uuid-1>', '<uuid-2>', '<uuid-3>');
   ```
4. Designate exactly **one** of those accounts as the adjudicator:
   ```sql
   UPDATE profiles SET is_adjudicator = true WHERE id = '<uuid-3>';
   ```

### 3. Conduct the Independent Annotation
This is the UX smoke test where you act as the researchers.
1. **Annotator 1:** Log into the frontend and navigate to `/annotate`.
   - Complete all 17 pairs.
   - *Diagnostic task:* Record the median/p95 load times for the images. Ensure signed URL latency is acceptable and there are zero loading failures.
2. **Annotator 2:** Log out, log into the second account, and navigate to `/annotate`.
   - Complete the same 17 pairs blindly.
   - *Diagnostic task:* Note any ambiguity in the taxonomy rubric (e.g., struggling to decide between "wrong clothing" and "wrong body feature").

### 4. Adjudicate Conflicting Pairs
1. Log in using the **Adjudicator** account and navigate to `/adjudicate`.
2. The UI will render *only* the pairs where Annotator 1 and Annotator 2 disagreed (on `same_character`, or any of the specific taxonomy checkboxes).
3. Submit the final, authoritative label for these conflicting pairs.

### 5. Export and Analyze Diagnostics
Since these pairs are seeded with `is_pilot = true`, the main Phase 2.5 export script (`build_dataset.py`) intentionally ignores them to avoid poisoning the training set.

To perform the pilot export:
1. Export the `annotations` table to CSV from your Supabase Dashboard.
2. Review your offline diagnostics:
   - Calculate raw agreement and your adjudication rate.
   - Identify specific taxonomy confusion categories (e.g. consistently disagreeing on `anatomy_intact`).

### 6. Formal Instrument Freeze
If the UI ergonomics were smooth, latency was minimal, and the export data is correctly structured:
1. Refine the annotation guide in `docs/specs/judge-finetune.md` if any rubric confusions were found.
2. Formally declare the taxonomy definitions and UI **frozen**. No further changes to the database schema, frontend UI, or taxonomy constraints are allowed before the full ~750-1000 dataset campaign begins.
3. Check off the assertions in `07-human-pilot.md`.
