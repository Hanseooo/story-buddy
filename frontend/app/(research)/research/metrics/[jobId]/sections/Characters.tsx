import ImageViewer from "../ImageViewer";
import type { RunCharacter } from "../types";
import SafetyBadge from "./SafetyBadge";

function Chips({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <div>
      <dt className="text-[11px] font-bold uppercase tracking-wider text-foreground/50">{label}</dt>
      <dd className="mt-1 flex flex-wrap gap-1.5">
        {values.map((value) => (
          <span key={value} className="rounded-md bg-muted/50 px-2 py-0.5 text-xs font-medium">{value}</span>
        ))}
      </dd>
    </div>
  );
}

export default function Characters({ characters }: { characters: RunCharacter[] }) {
  return (
    <section id="characters" aria-labelledby="characters-heading" className="scroll-mt-6 space-y-3">
      <h2 id="characters-heading" className="font-display text-2xl font-bold">Characters</h2>
      {characters.length === 0 ? (
        <p className="text-sm text-foreground/60">No characters were recorded.</p>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {characters.map((character) => (
            <li key={character.char_id} className="flex flex-col gap-4 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:flex-row">
              <ImageViewer src={character.ref_image_url} alt={`Reference for ${character.name}`} className="aspect-square w-full sm:w-40 sm:shrink-0" />
              <div className="flex min-w-0 flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-display text-xl font-bold">{character.name}</h3>
                  <SafetyBadge status={character.ref_moderation_status} label="Reference safety" />
                </div>
                <dl className="space-y-2">
                  <Chips label="Species" values={character.description.species ? [character.description.species] : []} />
                  <Chips label="Colours" values={character.description.colours} />
                  <Chips label="Body" values={character.description.body_features} />
                  <Chips label="Clothing" values={character.description.clothing} />
                </dl>
                {character.ref_verdict ? (
                  <div className="text-sm">
                    <p className={`font-bold ${character.ref_verdict.matches_description ? "text-success" : "text-destructive"}`}>
                      {character.ref_verdict.matches_description ? "Judge: matches the description" : "Judge: does not match the description"}
                    </p>
                    {character.ref_verdict.contradictions.length > 0 && (
                      <ul className="mt-1 list-disc space-y-0.5 pl-5 text-foreground/80">
                        {character.ref_verdict.contradictions.map((contradiction) => <li key={contradiction}>{contradiction}</li>)}
                      </ul>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-foreground/60">The reference was not judged.</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
