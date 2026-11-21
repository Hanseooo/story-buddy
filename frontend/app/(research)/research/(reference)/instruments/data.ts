// SH-02: every sentence below is copied from one of these tracked files. data.test.ts checks each one,
// and checks that the question and item lists have no more and no fewer entries than the forms.
export const SOURCES = {
  expert: "docs/capstone/expert-evaluation-questionnaire.md",
  iso: "docs/capstone/iso-25010-questionnaire.md",
  spec: "docs/specs/research-page-refresh.md",
} as const;

// US-17 AC-14, D-10: shown until a survey has been run.
export const PENDING = "Survey pending";

// O-04: the method for the seven open answers is not chosen.
export const ANALYSIS_TBD = "Content analysis or thematic analysis (to be decided)";

export const EXPERT = {
  evaluators: "Three evaluators: 2 Bachelor of Elementary Education (BEEd) professors and 1 Arts professor. Each signs the informed consent form first.",
  procedure: "Each reviews the original child-written story and the generated picture book, and fills in one questionnaire per book, with its Story ID.",
  format: "The form has seven open-ended questions and no rating scale.",
  answerStyle: "Answer each question in your own words. Give explanations and examples, not a numerical rating or a yes/no response.",
} as const;

// The heading is the question. The prompt is guidance for the answer, not a separate question.
export const QUESTIONS = [
  {
    n: 1,
    heading: "How appropriate and meaningful is the generated picture book for its intended readers?",
    prompt:
      "Consider the relevance and suitability of its topic or theme, the clarity of its central idea or message, and whether its content is appropriate for Grade 5 and Grade 6 readers.",
  },
  {
    n: 2,
    heading: "How effectively does the written language communicate the story and engage its intended readers?",
    prompt:
      "Consider clarity, vocabulary, sentence construction, grammar, dialogue, tone, mood, and the use of expressive or literary language where appropriate.",
  },
  {
    n: 3,
    heading: "How well are the characters and setting developed and represented throughout the picture book?",
    prompt:
      "Consider whether characters are understandable and distinguishable, whether their actions fit the story, and whether the setting is clear and supports the events.",
  },
  {
    n: 4,
    heading: "How coherent and effective is the development of the plot from beginning to end?",
    prompt:
      "Consider the sequence and connection of events, pacing, transitions, conflict or central situation, resolution, and whether important narrative details are missing, repeated, or confusing.",
  },
  {
    n: 5,
    heading: "How effectively do the illustrations communicate and support the written narrative?",
    prompt:
      "Consider visual clarity and appeal, relevance to the events, representation of characters and setting, the relationship between text and images, and the way the illustrations contribute to mood or meaning.",
  },
  {
    n: 6,
    heading: "How faithfully does the generated picture book represent the original child-written story?",
    prompt:
      "Consider whether the central idea, intended meaning, characters, key events, and important details are preserved, and whether any additions, omissions, or changes affect the child's intended narrative.",
  },
  {
    n: 7,
    heading:
      "Considering the generated picture book as a whole, how effective is its overall presentation and reading experience, and what improvements would you recommend?",
    prompt:
      "Consider the organization of pages, readability, placement of text and illustrations, visual flow, reader engagement, overall strengths, and specific improvements that could enhance the picture book.",
  },
];

export const ISO = {
  scale: "Each item is rated 1–5, where 5 = Strongly Agree and 1 = Strongly Disagree, so a higher mean is better.",
  rating: "5 = Strongly Agree, 4 = Agree, 3 = Neutral, 2 = Disagree, 1 = Strongly Disagree.",
  respondents: "At least 30 respondents in total, from IT experts, IT students, teachers and education students, not split equally.",
  statistics: "Descriptive statistics only: no Content Validity Index and no Cronbach's α pilot.",
  consent: "Respondents sign a consent form first.",
} as const;

type IsoGroup = { letter: string; name: string; description: string; items: readonly { n: number; text: string }[] };

export const ISO_GROUPS: readonly IsoGroup[] = [
  {
    letter: "A",
    name: "Functional Suitability",
    description: "whether StoryBuddy provides the functions needed to transform written stories into digital picture books.",
    items: [
      { n: 1, text: "StoryBuddy provides the necessary functions to complete the digital picture-book generation process." },
      { n: 2, text: "StoryBuddy allows users to submit written stories and provide the required information for processing." },
      { n: 3, text: "StoryBuddy correctly organizes submitted stories into a sequence of storyboard scenes." },
      { n: 4, text: "StoryBuddy generates the expected illustrations based on the information processed from each story scene." },
      { n: 5, text: "StoryBuddy provides the necessary functions to compile and export the generated picture book." },
    ],
  },
  {
    letter: "B",
    name: "Interaction Capability",
    description: "how easy StoryBuddy is to understand, learn, and operate.",
    items: [
      { n: 6, text: "StoryBuddy's interface makes its available functions and features easy to recognize." },
      { n: 7, text: "The instructions and information provided by the system make it easy to learn how to use its features." },
      { n: 8, text: "The available controls and options allow users to operate the system effectively." },
      { n: 9, text: "StoryBuddy provides appropriate feedback when users enter incomplete or invalid information." },
    ],
  },
  {
    letter: "C",
    name: "Reliability",
    description: "StoryBuddy's ability to perform its functions correctly and consistently under normal operating conditions.",
    items: [
      { n: 10, text: "StoryBuddy performs its intended functions without unexpected errors during normal use." },
      { n: 11, text: "StoryBuddy remains accessible and operational when needed under its intended operating conditions." },
      { n: 12, text: "StoryBuddy handles processing interruptions or operation failures without causing unnecessary disruption to other functions." },
      { n: 13, text: "StoryBuddy provides appropriate options to retry or recover an operation after an unexpected failure." },
      { n: 14, text: "StoryBuddy preserves submitted story information throughout the picture-book generation process." },
    ],
  },
  {
    letter: "D",
    name: "Performance Efficiency",
    description: "response time, picture book generation speed, and responsiveness during use.",
    items: [
      { n: 15, text: "StoryBuddy provides timely updates on the progress of picture-book generation." },
      { n: 16, text: "StoryBuddy completes picture-book generation within an acceptable amount of time under normal operating conditions." },
      { n: 17, text: "StoryBuddy maintains acceptable performance when processing stories within its expected workload and operating limits." },
    ],
  },
  {
    letter: "E",
    name: "Security",
    description: "how StoryBuddy protects submitted stories and associated information and communicates its data-handling practices.",
    items: [
      { n: 18, text: "StoryBuddy protects submitted stories and associated information from unauthorized disclosure." },
      { n: 19, text: "StoryBuddy protects stored story information against unauthorized modification." },
      { n: 20, text: "StoryBuddy provides appropriate means to identify or verify authorized users when accessing protected features." },
      { n: 21, text: "StoryBuddy provides safeguards against unauthorized attempts to access or compromise its functions and information." },
    ],
  },
  {
    letter: "F",
    name: "Compatibility",
    description:
      "StoryBuddy's ability to operate effectively within its intended computing environment and exchange information with connected systems or services.",
    items: [
      { n: 22, text: "StoryBuddy operates properly within its supported browsers and computing environments." },
      { n: 23, text: "StoryBuddy successfully exchanges the required information with its integrated AI services." },
    ],
  },
];
