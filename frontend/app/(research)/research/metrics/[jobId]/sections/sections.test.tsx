import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import fixture from "../__fixtures__/run.json";
import passedWithWarnings from "../__fixtures__/passed-with-warnings.json";
import type { RunDetail } from "../types";
import Pages from "./Pages";
import RawJson from "./RawJson";

const RUN = fixture as unknown as RunDetail;

describe("Pages", () => {
  it("marks the selected drawing and distinguishes required issues from warnings", () => {
    const { rerender } = render(<Pages scenes={RUN.scenes} characters={RUN.characters} objects={[]} />);

    const page1 = screen.getByRole("article", { name: "Page 1" });
    const attempts = within(page1).getAllByRole("listitem", { name: /^Attempt \d$/ });
    expect(attempts).toHaveLength(2);
    expect(within(attempts[0]).queryByText("Used in the book")).toBeNull();
    expect(within(attempts[0]).getByText("Failed required checks")).toBeInTheDocument();
    expect(within(attempts[0]).getByText("Character colour differs from the reference")).toBeInTheDocument();
    expect(within(attempts[1]).getByText("Used in the book")).toBeInTheDocument();
    expect(within(attempts[1]).getByRole("button", { name: "Enlarge Page 1, attempt 2" })).toBeInTheDocument();

    // Judge fields captured from the owner's synthetic run 4eea0e4c on 2026-10-10.
    const warnings = {
      ...RUN.scenes[1],
      attempts: [{
        ...RUN.scenes[1].attempts[0],
        ...passedWithWarnings,
      }],
    };
    rerender(<Pages scenes={[warnings]} characters={RUN.characters} objects={[]} />);
    expect(screen.getByText("Passed required checks")).toBeInTheDocument();
    expect(screen.getByText("Other warnings")).toBeInTheDocument();
    expect(screen.getByText("Text detected in the illustration")).toBeInTheDocument();
    expect(screen.getByText("Face differs from the character reference")).toBeInTheDocument();
    expect(screen.getByText("These observations do not reject the drawing on their own.")).toBeInTheDocument();
    expect(screen.queryByText("Required-check issues")).toBeNull();
  });

  it("says Not checked when the judge gave no answer", () => {
    const scene = {
      ...RUN.scenes[1],
      shipped_attempt: null,
      attempts: [{ ...RUN.scenes[1].attempts[0], passed: false, vlm_verdict: null }],
    };
    const { rerender } = render(<Pages scenes={[scene]} characters={RUN.characters} objects={[]} />);

    expect(screen.getByText("Not checked")).toBeInTheDocument();
    expect(screen.queryByText("Failed required checks")).toBeNull();

    const checked = {
      ...scene,
      attempts: [{ ...scene.attempts[0], scene_contradictions: RUN.scenes[0].attempts[0].failure_reasons }],
    };
    rerender(<Pages scenes={[checked]} characters={RUN.characters} objects={[]} />);
    expect(screen.getByText("Failed required checks")).toBeInTheDocument();
    expect(screen.queryByText("Not checked")).toBeNull();
  });
});

describe("RawJson", () => {
  it("copies the pretty-printed state", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    const state = RUN.cost as unknown as RunDetail["state"];
    const { container } = render(<RawJson state={state} />);
    container.querySelector("details")!.open = true;

    fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));

    expect(writeText).toHaveBeenCalledWith(
      '{\n  "image_count": 0,\n  "regen_count": 0,\n  "usd_estimate": 0,\n  "ref_retry_count": 0,\n  "ref_mod_retry_count": 0\n}'
    );
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });

  it("keeps the JSON available when clipboard access is refused", async () => {
    const writeText = vi.fn().mockRejectedValue(new Error("Clipboard unavailable"));
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    const state = RUN.cost as unknown as RunDetail["state"];
    const { container } = render(<RawJson state={state} />);
    container.querySelector("details")!.open = true;

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));
    });

    expect(screen.getByText("Copy")).toBeInTheDocument();
    expect(screen.getByText(/"image_count": 0/)).toBeInTheDocument();
  });
});
