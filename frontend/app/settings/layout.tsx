import TeacherShell from "@/components/TeacherShell";

export default async function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <TeacherShell>{children}</TeacherShell>;
}
