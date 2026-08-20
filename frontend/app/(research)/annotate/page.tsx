export const dynamic = "force-dynamic";

import Link from "next/link";
import { CheckCircle, ArrowLeft, WarningCircle } from "@phosphor-icons/react/dist/ssr";
import AnnotationClient from "./AnnotationClient";
import { getNextPair } from "./actions";

export const metadata = {
  title: "Annotate Image Pair · StoryBuddy Research Lab",
};

export default async function AnnotatePage() {
  const result = await getNextPair();
  const pair = result?.pair;
  const error = result?.error;

  if (error) {
    return (
      <div className="w-full flex-1 flex flex-col items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-lg bg-surface rounded-2xl neo-border neo-shadow-sm p-8 text-center flex flex-col items-center gap-4">
          <div className="size-14 rounded-2xl bg-destructive/15 text-destructive flex items-center justify-center">
            <WarningCircle weight="duotone" className="size-8" />
          </div>
          <h1 className="text-2xl font-display font-bold text-foreground">Error</h1>
          <p className="text-sm text-foreground/70 leading-relaxed max-w-[40ch]">
            {error}
          </p>
          <div className="pt-2">
            <Link
              href="/research"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-surface font-semibold text-sm hover:bg-primary-deep transition-all neo-shadow-xs"
            >
              <ArrowLeft weight="bold" className="size-4" />
              Back to Research Lab
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!pair) {
    return (
      <div className="w-full flex-1 flex flex-col items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-lg bg-surface rounded-2xl neo-border neo-shadow-sm p-8 text-center flex flex-col items-center gap-4">
          <div className="size-14 rounded-2xl bg-success/15 text-success flex items-center justify-center">
            <CheckCircle weight="duotone" className="size-8" />
          </div>
          <h1 className="text-2xl font-display font-bold text-foreground">Queue Complete</h1>
          <p className="text-sm text-foreground/70 leading-relaxed max-w-[40ch]">
            No pending pairs found in the annotation queue. All available pairs have been evaluated.
          </p>
          <div className="pt-2">
            <Link
              href="/research"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-surface font-semibold text-sm hover:bg-primary-deep transition-all neo-shadow-xs"
            >
              <ArrowLeft weight="bold" className="size-4" />
              Back to Research Lab
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <AnnotationClient pair={pair} />;
}
