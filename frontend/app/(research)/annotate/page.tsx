export const dynamic = "force-dynamic";

import AnnotationClient from "./AnnotationClient";
import { getNextPair } from "./actions";

export default async function AnnotatePage() {
  const result = await getNextPair();
  const pair = result?.pair;
  const error = result?.error;

  return (
    <div className="w-full max-w-6xl px-4 flex flex-col items-center pb-20">
      <h1 className="text-2xl font-bold mb-6">Annotate Image Pair</h1>
      
      {error || !pair ? (
        <div className="p-8 bg-white rounded-lg shadow text-center">
          <p className="text-gray-500">No pending pairs found in the queue.</p>
        </div>
      ) : (
        <AnnotationClient pair={pair} />
      )}
    </div>
  );
}
