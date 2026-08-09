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
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={`/avatars/${avatarId}.svg`}
        alt=""
        width={size}
        height={size}
        className="rounded-full object-cover shrink-0"
      />
    );
  }

  const initial = displayNickname.charAt(0).toUpperCase();
  return (
    <div
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      className="rounded-full bg-primary/10 flex items-center justify-center text-primary font-display font-extrabold shrink-0"
      aria-hidden="true"
    >
      {initial}
    </div>
  );
}
