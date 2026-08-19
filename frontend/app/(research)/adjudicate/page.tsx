import { getConflictedPair } from "./actions";
import AdjudicateClient from "./AdjudicateClient";

export const dynamic = "force-dynamic";

export default async function AdjudicatePage() {
  const result = await getConflictedPair();
  const pair = result?.pair;
  const annotationA = result?.annotationA;
  const annotationB = result?.annotationB;
  const error = result?.error;

  return (
    <div className="w-full max-w-6xl px-4 flex flex-col items-center pb-20">
      <h1 className="text-2xl font-bold mb-6 text-purple-900">Adjudicate Conflicts</h1>

      {error || !pair || !annotationA || !annotationB ? (
        <div className="p-8 bg-white rounded-lg shadow text-center w-full">
          <p className="text-gray-500">No conflicted pairs pending adjudication found.</p>
        </div>
      ) : (
        <AdjudicateClient pair={pair} annotationA={annotationA} annotationB={annotationB} />
      )}
    </div>
  );
}
