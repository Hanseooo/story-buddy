import { createClient } from "@supabase/supabase-js";

export async function createAdminClient() {
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  return createClient(supabaseUrl, serviceKey);
}
