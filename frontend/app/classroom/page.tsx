import { redirect } from "next/navigation";
import { getTeacherContext } from "@/utils/supabase/teacher";
import ClassroomPicker from "./ClassroomPicker";

export default async function ClassroomPickerPage() {
  const { classrooms } = await getTeacherContext();
  if (classrooms.length === 1) redirect(`/classroom/${classrooms[0].id}`);
  return <ClassroomPicker classrooms={classrooms} />;
}
