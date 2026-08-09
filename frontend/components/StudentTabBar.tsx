"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Book, ImageSquare, User } from "@phosphor-icons/react";

const TABS = [
  {
    label: "Bookshelf",
    Icon: Book,
    href: (id: string) => `/s/${id}`,
  },
  {
    label: "Gallery",
    Icon: ImageSquare,
    href: (id: string) => `/s/${id}/gallery`,
  },
  {
    label: "Profile",
    Icon: User,
    href: (id: string) => `/s/${id}/settings`,
  },
] as const;

export function StudentTabBar({ profileId }: { profileId: string }) {
  const pathname = usePathname();

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-surface border-t border-primary/15"
      style={{ paddingBottom: "env(safe-area-bottom-inset, env(safe-area-inset-bottom))" }}
    >
      <div className="flex">
        {TABS.map(({ label, Icon, href }) => {
          const path = href(profileId);
          const isActive = pathname === path;
          return (
            <Link
              key={label}
              href={path}
              aria-current={isActive ? "page" : undefined}
              className={[
                "font-kid flex flex-1 flex-col items-center gap-0.5 py-2 min-h-[44px]",
                "text-sm font-bold transition-all active:scale-[0.98]",
                isActive ? "text-primary" : "text-foreground/60",
              ].join(" ")}
            >
              <span aria-hidden="true" className="flex h-6 items-center justify-center">
                <Icon weight={isActive ? "fill" : "regular"} className="h-6 w-6" />
              </span>
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
