import TeacherShell from "@/components/TeacherShell";

export default async function ClassroomLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params?: Promise<{ classroomId?: string }>;
}) {
  const resolved = params ? await params : undefined;
  return (
    <TeacherShell classroomId={resolved?.classroomId}>{children}</TeacherShell>
  );
}
