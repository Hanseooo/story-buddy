import TeacherShell from "@/components/TeacherShell";

export default function ClassroomLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <TeacherShell>{children}</TeacherShell>;
}
