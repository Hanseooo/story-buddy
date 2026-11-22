import ScrollTable from "../../../_shared/components/ScrollTable";
import Source from "../../../_shared/components/Source";
import { MODELS } from "../architecture/data";
import { BASIS, CONSENT, LIMITS, MODERATION_LAYERS, PRIVACY, SAFETY_FEATURES, SOURCES, type Fact } from "./data";
import OnThisPage from "../../../_shared/components/OnThisPage";

export const metadata = {
  title: "StoryBuddy Ethics and Safety",
};

const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const H2 = "font-display text-2xl font-extrabold tracking-tight md:text-3xl";
const H3 = "font-display text-xl font-extrabold tracking-tight";
const TH = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-widest text-foreground/60";
const TD = "px-3 py-2 align-top";
const PROSE = "max-w-[70ch] text-foreground/80";

const SECTIONS = [
  { id: "basis", label: "Ethics basis" },
  { id: "consent", label: "Consent" },
  { id: "privacy", label: "Privacy" },
  { id: "safety", label: "Safety measures" },
];

const TERMS = [
  ["Personal information", "details that identify a person, such as a name, phone number or address"],
  ["Presidio", "an open-source tool that finds personal information in text and blanks it out"],
  ["Moderation", "a safety check on text or a picture before a child sees it"],
  ["Classifier", "a model that labels content as safe or unsafe"],
] as const;

const modelId = (setting: string) => MODELS.find((model) => model.setting === setting)!.id;

function Sentences({ facts, label }: { facts: readonly Fact[]; label: string }) {
  return (
    <ul aria-label={label} className={`${PROSE} list-disc space-y-2 pl-6 marker:text-primary`}>
      {facts.map((fact) => (
        <li key={fact.text}>{fact.text}</li>
      ))}
    </ul>
  );
}

export default function EthicsPage() {
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Ethics and safety</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          The basis the study rests on, what was consented to, what is public, and the safety measures as configured. Each statement is checked by a test against the file it comes from.
        </p>
      </div>

      <OnThisPage sections={SECTIONS} />

      <aside aria-label="Terms used on this page" className={`${CARD} space-y-2`}>
        <h2 className={H3}>Terms on this page</h2>
        <dl className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[10rem_1fr]">
          {TERMS.map(([term, meaning]) => (
            <div key={term} className="contents">
              <dt className="font-bold">{term}</dt>
              <dd className="text-foreground/80">{meaning}</dd>
            </div>
          ))}
        </dl>
      </aside>

      <section aria-labelledby="basis" className="space-y-4">
        <h2 id="basis" className={H2}>Ethics basis</h2>
        <Sentences facts={BASIS} label="The ethics basis" />
        <Source path={SOURCES.ethics} where="§5, Basis the study rests on (D-08)" />
      </section>

      <section aria-labelledby="consent" className="space-y-4">
        <h2 id="consent" className={H2}>Consent</h2>
        <Sentences facts={CONSENT} label="Consent" />
        <Source path={SOURCES.ethics} where="§5, Basis the study rests on (D-22)" />
        <Source path={SOURCES.spec} where="D-21, the expert evaluators' form" />
      </section>

      <section aria-labelledby="privacy" className="space-y-4">
        <h2 id="privacy" className={H2}>Privacy</h2>
        <Sentences facts={PRIVACY} label="Privacy disclosures" />
        <Source path={SOURCES.ethics} where="§1, PII Redaction, and §5, Public disclosure (D-09)" />
        <Source path={SOURCES.hardware} where="§6, Privacy posture, and §7, Hosting (D-07)" />
        <Source path={SOURCES.adr083} where="decision 5, synthetic material only" />
      </section>

      <section aria-labelledby="safety" className="space-y-6">
        <h2 id="safety" className={H2}>Safety measures</h2>

        <div className="space-y-4">
          <h3 className={H3}>Moderation layers</h3>
          <p className={PROSE}>
            Each layer, where it runs and which model checks it. An environment variable can override a model, so a deployment can differ. On a narrow screen, scroll the table sideways inside its box.
          </p>
          <ScrollTable label="Moderation layers and where each runs">
            <thead>
              <tr className="border-b border-primary/10">
                <th scope="col" className={TH}>Layer</th>
                <th scope="col" className={TH}>Where it runs</th>
                <th scope="col" className={TH}>Models</th>
                <th scope="col" className={TH}>What it does</th>
              </tr>
            </thead>
            <tbody>
              {MODERATION_LAYERS.map((layer) => (
                <tr key={layer.layer} className="border-b border-primary/5 last:border-0">
                  <th scope="row" className={`${TD} text-left font-bold`}>{layer.layer}</th>
                  <td className={TD}>
                    <span className="block text-foreground/80">{layer.runsIn}</span>
                    <span className="block font-mono text-xs break-all">{layer.file}</span>
                  </td>
                  <td className={TD}>
                    <ul className="space-y-1">
                      {layer.modelSettings.map((setting) => (
                        <li key={setting} className="font-mono text-xs break-all">{modelId(setting)}</li>
                      ))}
                    </ul>
                  </td>
                  <td className={`${TD} text-foreground/80`}>{layer.text}</td>
                </tr>
              ))}
            </tbody>
          </ScrollTable>
          <Source path="backend/app/config.py" where="the moderation model settings" />
          <Source path={SOURCES.ethics} where="§2, Moderation Pipeline and Ordering" />
        </div>

        <div className="space-y-4">
          <h3 className={H3}>Human checks and limits on features</h3>
          <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {SAFETY_FEATURES.map((feature) => (
              <li key={feature.name} className={`${CARD} space-y-1`}>
                <p className="font-bold">{feature.name}</p>
                <p className="text-sm text-foreground/80">{feature.text}</p>
              </li>
            ))}
          </ul>
          <Source path={SOURCES.ethics} where="§4 and §5, Later features" />
          <Source path={SOURCES.adr080} where="teacher-held moderation" />
          <Source path={SOURCES.adr081} where="teacher notes" />
          <Source path={SOURCES.adr082} where="magic pencil limits" />
          <Source path={SOURCES.config} where="enable_teacher_moderation_review, enable_magic_pencil, MAX_PENCIL_CHARS, MAX_PAGE_PENCILS" />
        </div>

        <div className="space-y-4">
          <h3 className={H3}>What is not claimed</h3>
          <Sentences facts={LIMITS} label="What is not claimed" />
        </div>
      </section>
    </main>
  );
}
