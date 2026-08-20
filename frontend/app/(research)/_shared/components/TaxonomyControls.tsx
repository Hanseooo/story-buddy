import { TaxonomyState } from "../constants";
import { TAXONOMY_LABELS } from "../constants";

type TaxonomyControlsProps = {
  isPending: boolean;
  explicitSameCharacter: boolean;
  setExplicitSameCharacter: (val: boolean) => void;
  taxonomy: TaxonomyState;
  toggleTaxonomy: (key: keyof TaxonomyState) => void;
  brokenAnatomy: boolean;
  setBrokenAnatomy: (val: boolean | ((prev: boolean) => boolean)) => void;
  textVisible: boolean;
  setTextVisible: (val: boolean | ((prev: boolean) => boolean)) => void;
  isSameCharacterSelected: boolean;
  setIsSameCharacterSelected: (val: boolean) => void;
};

export function TaxonomyControls({
  isPending,
  explicitSameCharacter,
  setExplicitSameCharacter,
  taxonomy,
  toggleTaxonomy,
  brokenAnatomy,
  setBrokenAnatomy,
  textVisible,
  setTextVisible,
  isSameCharacterSelected,
  setIsSameCharacterSelected,
}: TaxonomyControlsProps) {
  return (
    <div className="flex flex-col gap-6 flex-1">
      {/* TIER 1: Primary Identity Gate (Radio Group) */}
      <div className="flex flex-col gap-3">
        <label
          className={`relative flex items-center gap-3.5 p-3.5 rounded-xl border-2 transition-all cursor-pointer select-none ${
            isSameCharacterSelected && !explicitSameCharacter
              ? "bg-destructive/10 border-destructive/50 text-foreground shadow-sm"
              : "bg-surface border-muted hover:border-primary/40 hover:bg-primary/5 text-foreground"
          } ${isPending ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <input
            type="radio"
            name="character_identity"
            checked={isSameCharacterSelected && !explicitSameCharacter}
            onChange={() => {
              setIsSameCharacterSelected(true);
              setExplicitSameCharacter(false);
            }}
            disabled={isPending}
            className="size-5 border-muted text-destructive focus:ring-destructive accent-destructive"
          />
          <div className="flex-1 min-w-0">
            <span className="text-sm font-bold text-foreground block">
              Different Character
            </span>
            <p className="text-xs text-foreground/70 mt-0.5">
              Select one or more drift reasons below
            </p>
          </div>
          <kbd className="px-2.5 py-1 bg-surface border border-foreground/15 rounded-lg text-xs font-mono font-bold text-foreground/80 neo-shadow-xs">
            Shift+D
          </kbd>
        </label>

        <label
          className={`relative flex items-center gap-3.5 p-3.5 rounded-xl border-2 transition-all cursor-pointer select-none ${
            explicitSameCharacter
              ? "bg-success/15 border-success text-foreground shadow-sm"
              : "bg-surface border-muted hover:border-primary/40 hover:bg-primary/5 text-foreground"
          } ${isPending ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <input
            type="radio"
            name="character_identity"
            checked={explicitSameCharacter}
            onChange={() => {
              setIsSameCharacterSelected(true);
              setExplicitSameCharacter(true);
            }}
            disabled={isPending}
            data-testid="same-character-radio"
            className="size-5 border-muted text-success focus:ring-success accent-success"
          />
          <div className="flex-1 min-w-0">
            <span className="text-sm font-bold text-foreground block">
              Same Character
            </span>
            <p className="text-xs text-foreground/70 mt-0.5">
              Character maintains identity, core species, palette &amp; features
            </p>
          </div>
          <kbd className="px-2.5 py-1 bg-surface border border-foreground/15 rounded-lg text-xs font-mono font-bold text-foreground/80 neo-shadow-xs">
            0
          </kbd>
        </label>
      </div>

      {/* TIER 2: Failure Reasons Taxonomy (Keys 1-7) */}
      <div
        className={`flex flex-col gap-2 transition-opacity duration-200 ${
          explicitSameCharacter || !isSameCharacterSelected ? "opacity-50 pointer-events-none" : "opacity-100"
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-foreground/70">
            Character Drift Reasons
          </span>
          <span className="text-[11px] text-foreground/70">
            Multi-select (Keys 1–7)
          </span>
        </div>

        <div className="flex flex-col gap-1.5">
          {(
            Object.entries(TAXONOMY_LABELS) as [
              keyof TaxonomyState,
              { label: string; shortcut: string; example: string; description: string }
            ][]
          ).map(([key, { label, shortcut }]) => (
            <label
              key={key}
              className={`flex items-center gap-3 px-3 py-2 rounded-xl border transition-all cursor-pointer select-none group ${
                taxonomy[key]
                  ? "bg-primary/5 border-primary/40 text-foreground font-semibold shadow-sm"
                  : "bg-surface/60 border-muted hover:border-primary/30 hover:bg-primary/5 text-foreground/80"
              } ${isPending ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              <input
                type="checkbox"
                checked={taxonomy[key]}
                onChange={() => toggleTaxonomy(key)}
                disabled={isPending || explicitSameCharacter || !isSameCharacterSelected}
                aria-label={label}
                className="size-4.5 rounded border-muted text-primary focus:ring-primary accent-primary"
              />
              <span className="flex-1 text-xs sm:text-sm font-medium text-foreground">
                {label}
              </span>
              <kbd className="px-2 py-0.5 bg-surface border border-foreground/15 rounded text-xs text-foreground/70 font-mono">
                {shortcut}
              </kbd>
            </label>
          ))}
        </div>
      </div>

      {/* TIER 3: Visual Artifact & Quality Gates (Keys A, T) */}
      <div className="pt-2 border-t border-primary/10 flex flex-col gap-2 mt-auto">
        <div className="flex items-center justify-between">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-foreground/70">
            Artifact Gates
          </span>
          <span className="text-[11px] text-foreground/50">
            Independent Quality (A, T)
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <label
            className={`flex items-center gap-2.5 p-2.5 rounded-xl border transition-all cursor-pointer select-none ${
              brokenAnatomy
                ? "bg-warning/15 border-warning/50 text-foreground font-medium"
                : "bg-surface/60 border-muted hover:border-primary/30 hover:bg-primary/5 text-foreground/80"
            } ${isPending ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            <input
              type="checkbox"
              checked={brokenAnatomy}
              onChange={() => setBrokenAnatomy((p) => !p)}
              disabled={isPending}
              aria-label="Broken Anatomy"
              className="size-4 rounded border-muted text-warning focus:ring-warning accent-warning"
            />
            <span className="flex-1 text-xs font-medium text-foreground">
              Broken Anatomy
            </span>
            <kbd className="px-1.5 py-0.5 bg-surface border border-foreground/15 rounded text-[11px] text-foreground/70 font-mono">
              A
            </kbd>
          </label>

          <label
            className={`flex items-center gap-2.5 p-2.5 rounded-xl border transition-all cursor-pointer select-none ${
              textVisible
                ? "bg-warning/15 border-warning/50 text-foreground font-medium"
                : "bg-surface/60 border-muted hover:border-primary/30 hover:bg-primary/5 text-foreground/80"
            } ${isPending ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            <input
              type="checkbox"
              checked={textVisible}
              onChange={() => setTextVisible((p) => !p)}
              disabled={isPending}
              aria-label="Text Visible"
              className="size-4 rounded border-muted text-warning focus:ring-warning accent-warning"
            />
            <span className="flex-1 text-xs font-medium text-foreground">
              Text Visible
            </span>
            <kbd className="px-1.5 py-0.5 bg-surface border border-foreground/15 rounded text-[11px] text-foreground/70 font-mono">
              T
            </kbd>
          </label>
        </div>
      </div>
    </div>
  );
}
