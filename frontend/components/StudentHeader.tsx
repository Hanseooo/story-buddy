"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Book, ImageSquare, User } from "@phosphor-icons/react";
import { Avatar } from "@/components/Avatar";
import { motion } from "framer-motion";

type Props = {
  profileId: string;
  avatarId: string | null;
  displayNickname: string;
  classroomName: string | null;
};

export function StudentHeader({ profileId, avatarId, displayNickname, classroomName }: Props) {
  const pathname = usePathname();
  if (pathname === `/s/${profileId}/introduction` || pathname === `/s/${profileId}/change-password`) return null;
  return (
    <header className="bg-surface/95 backdrop-blur-md border-b border-primary/15 px-5 py-3 sm:px-8 z-40 sticky top-0">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <motion.div 
          className="flex min-w-0 flex-1 items-center gap-3"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
        >
          <motion.div
            className="shrink-0"
            whileHover={{ scale: 1.1, rotate: -5 }}
            whileTap={{ scale: 0.95 }}
          >
            <Avatar avatarId={avatarId} displayNickname={displayNickname} size={44} />
          </motion.div>
          <div className="min-w-0 [overflow-wrap:anywhere]">
            <p className="font-display text-xl sm:text-2xl font-extrabold text-primary">
              Hi, {displayNickname}!
            </p>
            {classroomName && (
              <p className="mt-0.5 font-kid text-base font-bold text-foreground/75">
                Class: {classroomName}
              </p>
            )}
          </div>
        </motion.div>
        <nav className="hidden md:flex shrink-0 items-center gap-6 text-sm font-bold text-foreground/80">
          <Link href={`/s/${profileId}`} className="flex items-center gap-2 hover:text-primary transition-colors">
            <Book weight="fill" className="h-5 w-5" aria-hidden="true" />
            Bookshelf
          </Link>
          <Link href={`/s/${profileId}/gallery`} className="flex items-center gap-2 hover:text-primary transition-colors">
            <ImageSquare weight="fill" className="h-5 w-5" aria-hidden="true" />
            Gallery
          </Link>
          <Link href={`/s/${profileId}/settings`} className="flex items-center gap-2 hover:text-primary transition-colors">
            <User weight="fill" className="h-5 w-5" aria-hidden="true" />
            Profile
          </Link>
        </nav>
      </div>
    </header>
  );
}
