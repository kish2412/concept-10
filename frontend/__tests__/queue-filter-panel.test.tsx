import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueueFilterPanel } from "@/components/encounters/queue-filter-panel";
import type { QueueFilters } from "@/types/encounter-queue";

describe("QueueFilterPanel", () => {
  const onChange = vi.fn();
  const defaultFilters: QueueFilters = {
    search: "",
    status: "",
    encounter_type: "",
    provider_id: "",
    department_id: "",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders filter labels", () => {
    render(
      <QueueFilterPanel filters={defaultFilters} onChange={onChange} open={true} />,
    );
    expect(screen.getByText("Filters")).toBeInTheDocument();
  });

  it("does NOT show reset button when no filters are active", () => {
    render(
      <QueueFilterPanel filters={defaultFilters} onChange={onChange} open={true} />,
    );
    expect(screen.queryByText(/reset/i)).not.toBeInTheDocument();
  });

  it("shows reset button when a filter is active", () => {
    render(
      <QueueFilterPanel
        filters={{ ...defaultFilters, status: "TRIAGE" }}
        onChange={onChange}
        open={true}
      />,
    );
    expect(screen.getByText(/reset/i)).toBeInTheDocument();
  });

  it("calls onChange with cleared filters when reset is clicked", async () => {
    const user = userEvent.setup();
    render(
      <QueueFilterPanel
        filters={{ ...defaultFilters, status: "TRIAGE", encounter_type: "EMERGENCY" }}
        onChange={onChange}
        open={true}
      />,
    );
    const resetBtn = screen.getByText(/reset/i);
    await user.click(resetBtn);
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        status: "",
        encounter_type: "",
        provider_id: "",
        department_id: "",
      }),
    );
  });

  it("renders select elements for status and type", () => {
    render(
      <QueueFilterPanel filters={defaultFilters} onChange={onChange} open={true} />,
    );
    // Check for selection trigger buttons/elements
    const triggers = screen.getAllByRole("combobox");
    expect(triggers.length).toBeGreaterThanOrEqual(2);
  });
});
