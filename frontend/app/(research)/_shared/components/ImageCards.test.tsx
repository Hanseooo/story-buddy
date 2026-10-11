import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EXAMPLES } from "../../research/(reference)/dataset/data";
import type { ResearchPair } from "../constants";
import { ImageCards } from "./ImageCards";

const sample = EXAMPLES.find((example) => example.record.pair_id === "033b8372e89e4c06")!;
const pair: ResearchPair = {
  id: sample.record.pair_id,
  canonical_signed_url: sample.reference.src,
  scene_signed_url: sample.page.src,
};

describe("ImageCards", () => {
  afterEach(() => vi.restoreAllMocks());

  it("reports loading, ready, failure, and retry while retaining the sample pair", () => {
    const onImageStateChange = vi.fn();
    render(
      <ImageCards
        pair={pair}
        onOpenLightbox={vi.fn()}
        setActiveLightboxTab={vi.fn()}
        onImageStateChange={onImageStateChange}
      />,
    );

    const images = screen.getAllByRole("img");
    expect(onImageStateChange).toHaveBeenLastCalledWith("loading");
    fireEvent.load(images[0]);
    fireEvent.load(images[1]);
    expect(onImageStateChange).toHaveBeenLastCalledWith("ready");

    fireEvent.error(images[1]);
    expect(onImageStateChange).toHaveBeenLastCalledWith("error");
    expect(screen.getByRole("alert")).toHaveTextContent(/sample image could not be loaded/i);

    fireEvent.click(screen.getByRole("button", { name: /retry sample images/i }));
    expect(onImageStateChange).toHaveBeenLastCalledWith("loading");
    expect(screen.getAllByRole("img").map((image) => image.getAttribute("src"))).toEqual([
      sample.reference.src,
      sample.page.src,
    ]);
  });

  // The server sends the images in the page, so one can fail before React attaches its error handler.
  it("offers retry for an image that failed before the page became interactive", () => {
    vi.spyOn(HTMLImageElement.prototype, "complete", "get").mockReturnValue(true);
    vi.spyOn(HTMLImageElement.prototype, "naturalWidth", "get").mockReturnValue(0);
    const onImageStateChange = vi.fn();
    render(
      <ImageCards
        pair={pair}
        onOpenLightbox={vi.fn()}
        setActiveLightboxTab={vi.fn()}
        onImageStateChange={onImageStateChange}
      />,
    );

    expect(onImageStateChange).toHaveBeenLastCalledWith("error");
    expect(screen.getByRole("button", { name: /retry sample images/i })).toBeInTheDocument();
  });

  it("keeps the existing card presentation when load reporting is not enabled", () => {
    render(
      <ImageCards pair={pair} onOpenLightbox={vi.fn()} setActiveLightboxTab={vi.fn()} />,
    );

    expect(screen.getByText("Visual Comparison")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
