"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  {
    label: "Bookshelf",
    icon: "📚",
    href: (id: string) => `/s/${id}`,
  },
  {
    label: "Gallery",
    icon: "🖼️",
    href: (id: string) => `/s/${id}/gallery`,
  },
  {
    label: "Profile",
    icon: "👤",
    href: (id: string) => `/s/${id}/settings`,
  },
] as const;

export function StudentTabBar({ profileId }: { profileId: string }) {
  const pathname = usePathname();

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-surface border-t border-primary/15"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="flex">
        {TABS.map(({ label, icon, href }) => {
          const path = href(profileId);
          const isActive = pathname === path;
          return (
            <Link
              key={label}
              href={path}
              aria-current={isActive ? "page" : undefined}
              className={[
                "flex flex-1 flex-col items-center gap-0.5 py-2 min-h-[44px]",
                "text-xs font-medium transition-colors",
                isActive ? "text-primary" : "text-muted-foreground",
              ].join(" ")}
            >
              <span aria-hidden="true" className="text-xl leading-none">
                {icon}
              </span>
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
