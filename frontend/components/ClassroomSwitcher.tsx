"use client";

type Classroom = { id: string; name: string };

export default function ClassroomSwitcher({
  classrooms,
  currentId,
}: {
  classrooms: Classroom[];
  currentId?: string;
}) {
  if (classrooms.length === 0) return null;
  return (
    <div className="relative">
      <select
        defaultValue={currentId ?? ""}
        onChange={(e) => {
          if (e.target.value) window.location.href = `/classroom/${e.target.value}`;
        }}
        className="text-sm font-bold bg-muted border border-primary/20 rounded-xl px-3 py-1.5 pr-8 appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary/30"
        aria-label="Switch classroom"
      >
        <option value="" disabled>
          {classrooms.length === 1 ? classrooms[0].name : "Select classroom"}
        </option>
        {classrooms.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-foreground/50 text-xs">
        ▾
      </span>
    </div>
  );
}
