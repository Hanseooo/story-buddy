import { AVATAR_IDS } from "@/lib/avatars";

type Props = {
  avatarId: string | null | undefined;
  displayNickname: string;
  size?: number;
};

export function Avatar({ avatarId, displayNickname, size = 48 }: Props) {
  const isValid =
    avatarId != null &&
    (AVATAR_IDS as readonly string[]).includes(avatarId);

  if (isValid) {
    return (
      <div 
        className="rounded-full shrink-0 flex items-center justify-center bg-surface ring-2 ring-primary/10 shadow-[0_2px_8px_rgba(49,85,217,0.08)] overflow-hidden"
        style={{ width: size, height: size }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/avatars/${avatarId}.svg`}
          alt=""
          width={size}
          height={size}
          className="w-full h-full object-cover"
        />
      </div>
    );
  }

  const initial = displayNickname.charAt(0).toUpperCase();
  return (
    <div
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      className="rounded-full bg-primary/10 flex items-center justify-center text-primary font-display font-extrabold shrink-0 ring-2 ring-primary/10 shadow-[0_2px_8px_rgba(49,85,217,0.08)]"
      aria-hidden="true"
    >
      {initial}
    </div>
  );
}
