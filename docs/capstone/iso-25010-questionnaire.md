# ISO/IEC 25010 Questionnaire (Objective 5)

**Source:** the paper form the owner supplied on 2026-11-21, transcribed from
`docs/specs/research-page-refresh/evidence/questionnaires-source.md` (D-27). The researchers' names
and contact details are left out on purpose, and so are signature lines.
**Status:** the form is final as supplied. No survey has been run yet (D-10, "Survey pending").

**Design (D-06, D-27).** 23 Likert items on 6 characteristics: Functional Suitability (items 1–5),
Interaction Capability (6–9), Reliability (10–14), Performance Efficiency (15–17), Security (18–21)
and Compatibility (22–23). Each item is rated 1–5, where 5 = Strongly Agree and 1 = Strongly
Disagree, so a higher mean is better. At least 30 respondents in total, from IT experts, IT
students, teachers and education students, not split equally. Descriptive statistics only: no
Content Validity Index and no Cronbach's α pilot. Respondents sign a consent form first.

This replaces the earlier five-characteristic draft (Functional suitability, Performance
efficiency, Usability, Reliability, Security; 1 = Poor to 5 = Excellent; CVI and α gates) in
`research_instruments.md`, `methodology.md` §6.3 and `iso-25010-scope-freeze.md`, now marked
superseded.

## Known mismatch in the paper consent form (O-12)

The consent text on the paper form disagrees with the questionnaire. The pages and docs use the
questionnaire's own values. The owner fixes the paper form (issue 137).

- It says "a 25-item questionnaire". The questionnaire has 23 items.
- It says "five software quality characteristics" but names six, and it names "Usability". Section B
  is titled Interaction Capability.
- Its role boxes (Teacher, IT Professional, IT Student (Graduating), Other) do not list education
  students, one of the four respondent groups in D-06.

## Informed consent (terms)

- Same study title as the expert questionnaire. Participation: use the StoryBuddy application and
  answer a questionnaire based on the ISO/IEC 25010 software quality model about the experience.
- Choices: agree / do not agree, with signature and date.

## Questionnaire — "Based on the ISO/IEC 25010:2023 Software Quality Model"

**Overview.** StoryBuddy is an AI-powered storyboarding and picture book generation system designed
to transform Grade 5 and 6 learners' written stories into digital picture books. It aims to support
teachers and pre-service educators in creating illustrated learning materials. The system processes
the submitted story, organizes it into storyboard scenes, generates corresponding illustrations, and
compiles the results into a digital picture book. The questionnaire evaluates the software quality of
the application: how well its features function, how users interact with the system, how reliably it
processes requests, how efficiently it performs generation tasks, and how securely it handles
submitted information.

**I. Evaluator information.** Name (optional); years of experience; professional position or role
(Teacher, IT Professional, IT Student (Graduating), Other); date.

**II. Instructions.** Rate each statement based on your experience using the application.
5 = Strongly Agree, 4 = Agree, 3 = Neutral, 2 = Disagree, 1 = Strongly Disagree.

**A. Functional Suitability** — whether StoryBuddy provides the functions needed to transform written
stories into digital picture books.
1. StoryBuddy provides the necessary functions to complete the digital picture-book generation
   process.
2. StoryBuddy allows users to submit written stories and provide the required information for
   processing.
3. StoryBuddy correctly organizes submitted stories into a sequence of storyboard scenes.
4. StoryBuddy generates the expected illustrations based on the information processed from each
   story scene.
5. StoryBuddy provides the necessary functions to compile and export the generated picture book.

**B. Interaction Capability** — how easy StoryBuddy is to understand, learn, and operate.
6. StoryBuddy's interface makes its available functions and features easy to recognize.
7. The instructions and information provided by the system make it easy to learn how to use its
   features.
8. The available controls and options allow users to operate the system effectively.
9. StoryBuddy provides appropriate feedback when users enter incomplete or invalid information.

**C. Reliability** — StoryBuddy's ability to perform its functions correctly and consistently under
normal operating conditions.
10. StoryBuddy performs its intended functions without unexpected errors during normal use.
11. StoryBuddy remains accessible and operational when needed under its intended operating
    conditions.
12. StoryBuddy handles processing interruptions or operation failures without causing unnecessary
    disruption to other functions.
13. StoryBuddy provides appropriate options to retry or recover an operation after an unexpected
    failure.
14. StoryBuddy preserves submitted story information throughout the picture-book generation process.

**D. Performance Efficiency** — response time, picture book generation speed, and responsiveness
during use.
15. StoryBuddy provides timely updates on the progress of picture-book generation.
16. StoryBuddy completes picture-book generation within an acceptable amount of time under normal
    operating conditions.
17. StoryBuddy maintains acceptable performance when processing stories within its expected workload
    and operating limits.

**E. Security** — how StoryBuddy protects submitted stories and associated information and
communicates its data-handling practices.
18. StoryBuddy protects submitted stories and associated information from unauthorized disclosure.
19. StoryBuddy protects stored story information against unauthorized modification.
20. StoryBuddy provides appropriate means to identify or verify authorized users when accessing
    protected features.
21. StoryBuddy provides safeguards against unauthorized attempts to access or compromise its functions
    and information.

**F. Compatibility** — StoryBuddy's ability to operate effectively within its intended computing
environment and exchange information with connected systems or services.
22. StoryBuddy operates properly within its supported browsers and computing environments.
23. StoryBuddy successfully exchanges the required information with its integrated AI services.
