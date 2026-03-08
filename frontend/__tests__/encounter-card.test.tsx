import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { EncounterCard } from "@/components/encounters/encounter-card";
import { buildEncounter } from "../fixtures";

describe("EncounterCard", () => {
  const onView = vi.fn();
  const onMoveNext = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders patient name and encounter id", () => {
    const enc = buildEncounter({
      patient: { id: "p1", first_name: "Alice", last_name: "Smith" },
      encounter_id: "ENC-20260101-ABCD",
    });
    render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    expect(screen.getByText("ENC-20260101-ABCD")).toBeInTheDocument();
  });

  it("falls back to truncated patient_id when patient is null", () => {
    const enc = buildEncounter({
      patient: null,
      patient_id: "abcdefgh-1234-5678-9012-345678901234",
    });
    render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    expect(screen.getByText("abcdefgh")).toBeInTheDocument();
  });

  it("shows chief complaint when present", () => {
    const enc = buildEncounter({ chief_complaint: "Severe headache" });
    render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    expect(screen.getByText("Severe headache")).toBeInTheDocument();
  });

  it("renders status badge with correct label", () => {
    const enc = buildEncounter({ status: "WITH_PROVIDER" });
    render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    expect(screen.getByText("In Consultation")).toBeInTheDocument();
  });

  it("renders type badge with correct label", () => {
    const enc = buildEncounter({ encounter_type: "EMERGENCY" });
    render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    expect(screen.getByText("Emergency")).toBeInTheDocument();
  });

  it("does not show next-status button when status is DISCHARGED", () => {
    const enc = buildEncounter({ status: "DISCHARGED" });
    render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    // DISCHARGED has no NEXT_STATUS mapping
    const buttons = screen.getAllByRole("button");
    // Only the View button should exist (no ArrowRight / Move Next)
    expect(buttons).toHaveLength(1);
  });

  it("shows assign-provider button when onAssign is provided", () => {
    const onAssign = vi.fn();
    const enc = buildEncounter();
    render(
      <EncounterCard
        encounter={enc}
        onView={onView}
        onMoveNext={onMoveNext}
        onAssign={onAssign}
      />,
    );
    // View + MoveNext + Assign = 3 buttons
    expect(screen.getAllByRole("button")).toHaveLength(3);
  });

  it("calls onView when view button is clicked", async () => {
    const user = userEvent.setup();
    const enc = buildEncounter();
    render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    const viewBtn = screen.getAllByRole("button")[0];
    await user.click(viewBtn);
    expect(onView).toHaveBeenCalledWith(enc);
  });

  it("calls onMoveNext when next-status button is clicked", async () => {
    const user = userEvent.setup();
    const enc = buildEncounter({ status: "CHECKED_IN" });
    render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    // Second button is the MoveNext button
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]);
    expect(onMoveNext).toHaveBeenCalledWith(enc);
  });

  it("applies alert styling when wait exceeds 30 minutes", () => {
    const enc = buildEncounter({
      checked_in_at: new Date(Date.now() - 35 * 60_000).toISOString(), // 35 min ago
      status: "CHECKED_IN",
    });
    const { container } = render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    // Alert border class should be applied
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("border-red");
  });

  it("does NOT apply alert styling when status is DISCHARGED even if wait is long", () => {
    const enc = buildEncounter({
      checked_in_at: new Date(Date.now() - 60 * 60_000).toISOString(), // 60 min ago
      status: "DISCHARGED",
    });
    const { container } = render(
      <EncounterCard encounter={enc} onView={onView} onMoveNext={onMoveNext} />,
    );
    const card = container.firstChild as HTMLElement;
    expect(card.className).not.toContain("border-red");
  });
});
