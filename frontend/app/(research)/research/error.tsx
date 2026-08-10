"use client";

export default function Error({ error }: { error: Error }) {
  return <div className="p-8 text-center text-red-500">Failed to load metrics: {error.message}</div>;
}
