import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DatasetPage from "./page";

const GITHUB = "https://github.com/Hanseooo/story-buddy/blob/main/";

describe("/research/dataset", () => {
  it("shows the split sizes with the file they come from", () => {
    render(<DatasetPage />);

    const splits = screen.getByRole("table", { name: /pairs in each split/i });
    const test = within(splits).getByRole("row", { name: /Held-out test/ });
    expect(within(test).getByText("329")).toBeInTheDocument();
    expect(within(test).getByText("47")).toBeInTheDocument();
    expect(screen.getByText(/16 disputed synthetic training pairs.*468.*all 484/i)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /research_runbook\.md/ })[0]).toHaveAttribute(
      "href",
      `${GITHUB}docs/capstone/research_runbook.md`
    );
  });

  it("counts human and non-human characters by species and says what changed", () => {
    render(<DatasetPage />);

    const kinds = screen.getByRole("table", { name: /human and non-human training and validation pairs/i });
    const train = within(kinds).getByRole("row", { name: /Train/ });
    expect(within(train).getByText("178")).toBeInTheDocument();
    expect(within(train).getByText("306")).toBeInTheDocument();
    expect(within(train).getByText("12")).toBeInTheDocument();
    expect(within(train).getByText("32")).toBeInTheDocument();
    expect(screen.getByText(/counted 7 animals or machines as human/i)).toBeInTheDocument();
    expect(screen.queryByText(/intake-declared non-human roster/i)).not.toBeInTheDocument();
  });

  it("defines the page's words in a box before any table", () => {
    render(<DatasetPage />);

    const box = screen.getByRole("region", { name: /words used on this page/i });
    for (const term of ["Pair", "Natural pair", "Constructed pair", "Study owner", "Freeze (registered)", "Seed", "Checkpoint"]) {
      expect(within(box).getByText(term)).toBeInTheDocument();
    }
    expect(box).toHaveTextContent(/same character as the reference/i);
    const firstTable = screen.getAllByRole("table")[0];
    expect(box.compareDocumentPosition(firstTable) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("says what a pair is, what counts as a page drawing, and the totals", () => {
    render(<DatasetPage />);

    const section = screen.getByRole("region", { name: /what is a pair/i });
    expect(section).toHaveTextContent(/both pictures show the same character/i);
    expect(section).toHaveTextContent(/rejected ones/i);
    expect(section).toHaveTextContent(/422 of the 795 natural pairs/);
    expect(section).toHaveTextContent(/page with two characters makes two pairs/i);
    expect(section).toHaveTextContent(/899 pairs from 42 books/);
    expect(section).toHaveTextContent(/795 are natural pairs/);
    expect(section).toHaveTextContent(/104 are constructed pairs/);
  });

  it("lists the ten steps with the dataset-flow figure and its downloads", () => {
    render(<DatasetPage />);

    const steps = screen.getByRole("list", { name: /the ten steps from story to test/i });
    expect(within(steps).getAllByRole("listitem")).toHaveLength(10);
    expect(within(steps).getAllByRole("listitem")[9]).toHaveTextContent(/329 held-out test pairs.*once/i);

    const figure = screen.getByRole("figure", { name: /dataset build and annotation flow/i });
    expect(within(figure).getByRole("img")).toHaveAttribute("src", "/research/diagrams/dataset_build_and_annotation_flow.drawio.svg");
    expect(within(figure).getByRole("img").getAttribute("alt")).toMatch(/stories.*books.*pairs.*raters/i);
    expect(figure).toHaveTextContent("As of 2026-11-21");
    const download = within(figure).getByRole("link", { name: /dataset_build_and_annotation_flow\.png/ });
    expect(download).toHaveAttribute("href", "/research/diagrams/dataset_build_and_annotation_flow.png");
    expect(download).toHaveAttribute("download", "dataset_build_and_annotation_flow.png");
    expect(within(figure).getByRole("link", { name: /dataset_build_and_annotation_flow\.drawio\.svg/ })).toHaveAttribute(
      "href",
      `${GITHUB}docs/diagrams/drawio/dataset_build_and_annotation_flow.drawio.svg`
    );
  });

  it("shows one real record in a box that scrolls and explains every field", () => {
    render(<DatasetPage />);

    const box = screen.getByRole("region", { name: /one record, as stored/i });
    expect(box).toHaveAttribute("tabindex", "0");
    expect(box).toHaveTextContent('"pair_id": "033b8372e89e4c06"');
    expect(box).toHaveTextContent('"label": false');
    expect(box).toHaveTextContent("assets/ref/syn-025--campaign-…_ref-c0-1.png");

    const fields = screen.getByRole("table", { name: /what each field of a record means/i });
    expect(within(fields).getAllByRole("row")).toHaveLength(14); // header + 13 fields
    expect(within(fields).getByRole("row", { name: /^label /i })).toHaveTextContent(/opposite of same_character.*true means Different/i);
    expect(within(fields).getByRole("row", { name: /differences_observed/ })).toHaveTextContent(/no rater wrote it/i);
  });

  it("explains who labelled, keeps clothing-or-style-is-Same beside the reasons table, and fixes the old claims", () => {
    render(<DatasetPage />);

    const section = screen.getByRole("region", { name: /how a pair was labelled/i });
    expect(within(section).getByRole("table", { name: /reasons a pair is different/i })).toBeInTheDocument();
    expect(section).toHaveTextContent(/Clothing or art style alone is Same/);
    expect(section).toHaveTextContent(/two group members labelled all 795 natural pairs/i);
    expect(section).toHaveTextContent(/172 pairs/);
    expect(section).toHaveTextContent(/85 of them/);
    expect(section).toHaveTextContent(/could see which rater gave which label/i);
    expect(section).toHaveTextContent(/constructed pairs were not labelled by anyone/i);
    expect(section).toHaveTextContent(/23 final labels differ from both raters/i);
    expect(section).toHaveTextContent(/9 final labels are Different with only Wrong Clothing or Wrong Style ticked/);
    expect(section).toHaveTextContent(/train 6, validation 1, test 2/);
    expect(screen.queryByText(/No test label changed/)).not.toBeInTheDocument();
  });

  it("names the reasons the team built its own labelling tool and links its demo spec", () => {
    render(<DatasetPage />);

    const section = screen.getByRole("region", { name: /why the team built its own labelling tool/i });
    for (const reason of ["It saves time.", "Both raters can label in parallel.", "Every label saves to the cloud as it is made.", "It is easy for teammates to use."]) {
      expect(within(section).getByText(reason)).toBeInTheDocument();
    }
    expect(section).toHaveTextContent(/short-lived signed links/i);
    expect(section).toHaveTextContent(/signing in as a researcher/i);
    expect(within(section).getAllByRole("link", { name: /research-labelling-demo\.md/ })[0]).toHaveAttribute(
      "href",
      `${GITHUB}docs/specs/research-labelling-demo.md`
    );
  });

  it("gives the split decisions and why the test set is donated stories only", () => {
    render(<DatasetPage />);

    const section = screen.getByRole("region", { name: /how the splits were made, and why/i });
    expect(section).toHaveTextContent(/no story or character is in two splits/i);
    expect(section).toHaveTextContent(/8 train stories and 2 validation stories/i);
    expect(section).toHaveTextContent(/12 of the 15 donated candidate stories/i);
    expect(section).toHaveTextContent(/too few donated characters/i);
    expect(section).toHaveTextContent(/real children.s writing/i);
    expect(section).toHaveTextContent(/only 4 Different pairs/i);
    expect(section).toHaveTextContent(/Reason not recorded/);
    expect(section).toHaveTextContent(/14 hand-picked character matches/i);
    expect(section).toHaveTextContent(/12 of them human with human/i);
    expect(section).not.toHaveTextContent(/maximi[sz]e/i);
    // One base per sentence: 53 + 104 = 157 of train's Different pairs.
    expect(section).toHaveTextContent(/157 Different pairs, 104 are constructed and 53 come from the app/i);
  });

  it("says the examples are hand-picked and that no test pair is shown", () => {
    render(<DatasetPage />);

    expect(screen.getAllByText(/hand-picked/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/no test pair is shown/i)).toBeInTheDocument();
  });

  it("shows each example as a reference and a page with its label", () => {
    render(<DatasetPage />);

    const examples = screen.getAllByRole("article");
    expect(examples).toHaveLength(6);
    expect(examples.filter((example) => within(example).queryByText("Same character"))).toHaveLength(3);
    expect(examples.filter((example) => within(example).queryByText("Different character"))).toHaveLength(3);
    for (const example of examples) expect(within(example).getAllByRole("img")).toHaveLength(2);
  });

  // ADR-066 decision 1.
  it("lets the reader open each example's frozen record", () => {
    render(<DatasetPage />);

    const examples = screen.getAllByRole("article");
    for (const example of examples) expect(within(example).getByText("Frozen record")).toBeInTheDocument();

    const constructed = examples[5];
    expect(constructed).toHaveTextContent('"pair_id": "848c636f47f8e342"');
    expect(constructed).toHaveTextContent('"pair_type": "constructed"');
    expect(constructed).toHaveTextContent("Not shown to the raters");
    expect(examples[0]).toHaveTextContent("Both raters first answered Same");
  });

  // ADR-066 decisions 3 and 10.
  it("shows one training record and states the two contradictory pairs", () => {
    render(<DatasetPage />);

    expect(screen.getByText(/The FIRST image is a canonical character reference/)).toBeInTheDocument();
    expect(screen.getByText(/"style_match": false/)).toBeInTheDocument();
    expect(screen.getByText(/the same fixed value in every training record/i)).toBeInTheDocument();
    expect(screen.getByText(/the training file holds those two image pairs with both answers/i)).toBeInTheDocument();
  });

  it("uses one vocabulary", () => {
    const { container } = render(<DatasetPage />);

    expect(container.textContent).not.toMatch(/pipeline pair/i);
  });
});
