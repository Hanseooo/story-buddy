import ChartFigure from "../../../_shared/components/ChartFigure";
import ScrollTable from "../../../_shared/components/ScrollTable";
import Source from "../../../_shared/components/Source";
import { BACKEND_LIBS, COMPONENTS, DEV_HARDWARE, DIAGRAM, FRONTEND_LIBS, HOSTING, MODELS, OWNER_TO_SUPPLY, PYTHON_VERSION, RUNBOOK_GPU_LINE, SOURCES, TRAINING } from "./data";

export const metadata = {
  title: "StoryBuddy System Architecture and Specifications",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const H2 = "font-display text-2xl font-extrabold tracking-tight md:text-3xl";
const TH = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-widest text-foreground/60";
const TD = "px-3 py-2 align-top";
const PROSE = "max-w-[70ch] text-foreground/80";
const CODE = "font-mono text-xs break-all";
const CUE = "text-sm text-foreground/60";

const SECTIONS = [
  { id: "diagram", label: "Diagram" },
  { id: "components", label: "Components" },
  { id: "models", label: "Models" },
  { id: "libraries", label: "Libraries" },
  { id: "training", label: "Training" },
  { id: "hosting", label: "Hosting" },
  { id: "development", label: "Development" },
];

const TERMS = [
  ["Presidio", "an open-source tool that finds personal information in text and blanks it out"],
  ["Moderation", "a safety check on text or a picture before a child sees it"],
  ["Queue", "a waiting line of jobs. The web service adds a job, and the worker takes it"],
  ["QLoRA", "a way to fine-tune a large model on one GPU by training a small add-on to it"],
  ["VRAM", "the memory on a graphics card"],
  ["CUDA", "the software layer that lets training code use an NVIDIA GPU"],
] as const;

export default function ArchitecturePage() {
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">System architecture and specifications</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          What runs where, and the exact models, libraries and hardware behind it. Each value names the file it is read from. A test fails when the file and this page disagree.
        </p>
      </div>

      <nav aria-label="On this page">
        <ul className="flex flex-wrap gap-2">
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a
                href={`#${section.id}`}
                className={`inline-flex min-h-11 items-center rounded-xl border border-primary/20 bg-surface px-3 text-sm font-bold text-primary hover:bg-primary/5 ${FOCUS}`}
              >
                {section.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <aside aria-label="Terms used on this page" className={`${CARD} space-y-2`}>
        <h2 className="font-display text-xl font-extrabold tracking-tight">Terms on this page</h2>
        <dl className="grid gap-x-4 gap-y-1 text-sm sm:grid-cols-[8rem_1fr]">
          {TERMS.map(([term, meaning]) => (
            <div key={term} className="contents">
              <dt className="font-bold">{term}</dt>
              <dd className="text-foreground/80">{meaning}</dd>
            </div>
          ))}
        </dl>
      </aside>

      <section aria-labelledby="diagram" className="space-y-4">
        <h2 id="diagram" className={H2}>The system, as built</h2>
        <p className={PROSE}>
          Browsers talk to a Next.js frontend on Vercel. A FastAPI web service on Northflank takes each story, checks it and queues a job. A worker runs the pipeline and calls the hosted models. On a narrow screen, scroll the diagram sideways.
        </p>
        <ChartFigure
          id="system-architecture"
          wide
          alt={DIAGRAM.alt}
          asOf={DIAGRAM.asOf}
          png={DIAGRAM.png}
          source={DIAGRAM.source}
          caption={<span className="block text-base font-bold text-foreground">System architecture diagram</span>}
        >
          <div
            role="region"
            aria-label="Diagram. It scrolls sideways on a narrow screen."
            tabIndex={0}
            className={`overflow-x-auto rounded-2xl border border-primary/10 bg-white ${FOCUS}`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={DIAGRAM.png} alt={DIAGRAM.alt} width={3848} height={2008} className="h-auto w-full min-w-[56rem]" />
          </div>
        </ChartFigure>
        <Source path={SOURCES.architectureDoc} where="the written description of the same system" />
      </section>

      <section aria-labelledby="components" className="space-y-4">
        <h2 id="components" className={H2}>Components</h2>
        <p className={PROSE}>One row per component, with its role and the file that holds it. On a narrow screen, scroll the table sideways inside its box.</p>
        <ScrollTable label="Components table">
          <thead>
            <tr className="border-b border-primary/10">
              <th scope="col" className={TH}>Component</th>
              <th scope="col" className={TH}>Role</th>
              <th scope="col" className={TH}>Source file</th>
            </tr>
          </thead>
          <tbody>
            {COMPONENTS.map((component) => (
              <tr key={component.name} className="border-b border-primary/5 last:border-0">
                <th scope="row" className={`${TD} w-[22%] text-left font-bold`}>{component.name}</th>
                <td className={`${TD} text-foreground/80`}>{component.role}</td>
                <td className={TD}>
                  <ul className="space-y-1">
                    {component.files.map((file) => (
                      <li key={file} className={CODE}>{file}</li>
                    ))}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <Source path="backend/app/main.py" where="lines 171 to 200 hold the web-tier redaction and title check" />
        <Source path={SOURCES.procfile} where="the web and worker processes" />
      </section>

      <section aria-labelledby="models" className="space-y-4">
        <h2 id="models" className={H2}>Models in use</h2>
        <p className={PROSE}>Each ID is the default in the named setting. An environment variable can override a setting, so a deployment can differ.</p>
        <ScrollTable label="Model IDs from config.py">
          <thead>
            <tr className="border-b border-primary/10">
              <th scope="col" className={TH}>Role</th>
              <th scope="col" className={TH}>Model ID</th>
              <th scope="col" className={TH}>Setting</th>
              <th scope="col" className={TH}>Host</th>
            </tr>
          </thead>
          <tbody>
            {MODELS.map((model) => (
              <tr key={model.setting} className="border-b border-primary/5 last:border-0">
                <th scope="row" className={`${TD} text-left font-bold`}>{model.role}</th>
                <td className={`${TD} font-mono text-xs`}>{model.id}</td>
                <td className={`${TD} font-mono text-xs`}>{model.setting}</td>
                <td className={`${TD} text-foreground/80`}>{model.host}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <p className={CUE}>The fine-tuned judge is not in this table. It is not deployed. Its training setup is below.</p>
        <Source path={SOURCES.config} where="the Settings class" />
        <Source path={SOURCES.techStack} where="§1, the same models with licences" />
      </section>

      <section aria-labelledby="libraries" className="space-y-4">
        <h2 id="libraries" className={H2}>Libraries</h2>
        <p className={PROSE}>
          {`Backend versions are the ranges declared in pyproject.toml, with Python ${PYTHON_VERSION}. Frontend versions are the ones in package.json.`}
        </p>
        <div className="grid grid-cols-1 gap-6">
          <ScrollTable label="Backend library versions">
            <thead>
              <tr className="border-b border-primary/10">
                <th scope="col" className={TH}>Library</th>
                <th scope="col" className={TH}>Declared</th>
                <th scope="col" className={TH}>Used for</th>
              </tr>
            </thead>
            <tbody>
              {BACKEND_LIBS.map((lib) => (
                <tr key={lib.name} className="border-b border-primary/5 last:border-0">
                  <th scope="row" className={`${TD} text-left font-mono text-xs font-bold`}>{lib.name}</th>
                  <td className={`${TD} font-mono text-xs whitespace-nowrap`}>{lib.version}</td>
                  <td className={`${TD} text-foreground/80`}>{lib.role}</td>
                </tr>
              ))}
            </tbody>
          </ScrollTable>
          <ScrollTable label="Frontend library versions">
            <thead>
              <tr className="border-b border-primary/10">
                <th scope="col" className={TH}>Library</th>
                <th scope="col" className={TH}>Declared</th>
                <th scope="col" className={TH}>Used for</th>
              </tr>
            </thead>
            <tbody>
              {FRONTEND_LIBS.map((lib) => (
                <tr key={lib.name} className="border-b border-primary/5 last:border-0">
                  <th scope="row" className={`${TD} text-left font-mono text-xs font-bold`}>{lib.name}</th>
                  <td className={`${TD} font-mono text-xs whitespace-nowrap`}>{lib.version}</td>
                  <td className={`${TD} text-foreground/80`}>{lib.role}</td>
                </tr>
              ))}
            </tbody>
          </ScrollTable>
        </div>
        <Source path={SOURCES.pyproject} where="dependencies and requires-python" />
        <Source path={SOURCES.packageJson} where="dependencies and devDependencies" />
      </section>

      <section aria-labelledby="training" className="space-y-4">
        <h2 id="training" className={H2}>Where the judge was trained</h2>
        <p className={PROSE}>
          The registered judge training (three seeds) ran on a rented cloud GPU. The run record is not in the repository, so its values were copied into the hardware doc. All three seeds report the same hardware. The record does not name the GPU provider.
        </p>
        <ScrollTable label="Training hardware values">
          <thead>
            <tr className="border-b border-primary/10">
              <th scope="col" className={TH}>Item</th>
              <th scope="col" className={TH}>Value</th>
            </tr>
          </thead>
          <tbody>
            {TRAINING.map((row) => (
              <tr key={row.item} className="border-b border-primary/5 last:border-0">
                <th scope="row" className={`${TD} w-[28%] text-left font-bold`}>{row.item}</th>
                <td className={TD}>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <Source path={SOURCES.hardware} where="§7, Training hardware" />
      </section>

      <section aria-labelledby="hosting" className="space-y-4">
        <h2 id="hosting" className={H2}>Where it runs</h2>
        <p className={PROSE}>The owner chose the Northflank region for its free tier. A school needs only a web browser and an internet connection.</p>
        <ScrollTable label="Hosting values">
          <thead>
            <tr className="border-b border-primary/10">
              <th scope="col" className={TH}>Part</th>
              <th scope="col" className={TH}>Where</th>
            </tr>
          </thead>
          <tbody>
            {HOSTING.map((row) => (
              <tr key={row.item} className="border-b border-primary/5 last:border-0">
                <th scope="row" className={`${TD} w-[34%] text-left font-bold`}>{row.item}</th>
                <td className={TD}>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <Source path={SOURCES.hardware} where="§7, Hosting, and §3b, what a school needs" />
        <Source path={SOURCES.techStack} where="§2, Services and infrastructure" />
      </section>

      <section aria-labelledby="development" className="space-y-4">
        <h2 id="development" className={H2}>Development machine</h2>
        <p className={PROSE}>
          Only the graphics card is confirmed. The other rows say who must supply them.
        </p>
        <ScrollTable label="Development hardware values">
          <thead>
            <tr className="border-b border-primary/10">
              <th scope="col" className={TH}>Item</th>
              <th scope="col" className={TH}>Value</th>
            </tr>
          </thead>
          <tbody>
            {DEV_HARDWARE.map((row) => (
              <tr key={row.item} className="border-b border-primary/5 last:border-0">
                <th scope="row" className={`${TD} w-[28%] text-left font-bold`}>{row.item}</th>
                <td className={`${TD} ${row.value === OWNER_TO_SUPPLY ? "text-foreground/60" : "font-bold"}`}>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <Source path={SOURCES.runbook} where={`line ${RUNBOOK_GPU_LINE}, the laptop's RTX 3050 Ti with 4 GB VRAM`} />
        <Source path={SOURCES.hardware} where="§3a, where the owner adds the other rows" />
      </section>
    </main>
  );
}
