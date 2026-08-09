import { render, screen } from "@testing-library/react";
import { expect, it, describe } from "vitest";
import { Avatar } from "./Avatar";

// spec §8 test 12 — manifest integrity
import { AVATAR_IDS } from "@/lib/avatars";
import * as fs from "node:fs";
import * as path from "node:path";

describe("Avatar", () => {
  // spec §8 test 6
  it("renders the letter circle when avatarId is null", () => {
    render(<Avatar avatarId={null} displayNickname="Tala" />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByText("T")).toBeDefined();
  });

  // spec §8 test 7
  it("renders the letter circle when avatarId is not in AVATAR_IDS", () => {
    render(<Avatar avatarId="peeps-99" displayNickname="Tala" />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.getByText("T")).toBeDefined();
  });

  // spec §8 test 8 — alt="" makes role "presentation"; querySelector finds it regardless
  it("renders <img> with correct src and empty alt for a valid avatarId", () => {
    const { container } = render(<Avatar avatarId="peeps-01" displayNickname="Tala" />);
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img!.getAttribute("src")).toBe("/avatars/peeps-01.svg");
    expect(img!.getAttribute("alt")).toBe("");
  });
});

// spec §8 test 12 — run only in Node (not jsdom)
describe("Manifest integrity", () => {
  it("every id in AVATAR_IDS has a matching file in public/avatars/", () => {
    const avatarDir = path.resolve(
      __dirname,
      "..",
      "public",
      "avatars"
    );
    for (const id of AVATAR_IDS) {
      const filePath = path.join(avatarDir, `${id}.svg`);
      expect(fs.existsSync(filePath), `missing file: ${id}.svg`).toBe(true);
    }
    const svgFiles = fs.readdirSync(avatarDir).filter((f) => f.endsWith(".svg"));
    expect(svgFiles.length).toBe(AVATAR_IDS.length);
  });
});
