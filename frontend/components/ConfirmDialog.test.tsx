import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ConfirmDialog from "./ConfirmDialog";

describe("ConfirmDialog", () => {
  it("is named by its title", () => {
    render(
      <ConfirmDialog open onConfirm={() => {}} onCancel={() => {}}
        title="Delete Grade 3?" description="This cannot be undone." confirmLabel="Yes, delete" />
    );
    // jsdom has no showModal(), so the dialog stays outside the accessibility tree.
    expect(screen.getByRole("dialog", { name: "Delete Grade 3?", hidden: true })).toBeInTheDocument();
  });
});
