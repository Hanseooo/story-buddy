import { getTeacherContext } from "@/utils/supabase/teacher";
import ClassroomPicker from "./ClassroomPicker";

export default async function ClassroomPickerPage() {
  const { classrooms } = await getTeacherContext();
  return <ClassroomPicker classrooms={classrooms} />;
}
