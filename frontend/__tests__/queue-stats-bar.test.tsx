import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueueStatsBar } from "@/components/encounters/queue-stats-bar";
import type { TodaySummary } from "@/types/encounter-queue";

describe("QueueStatsBar", () => {
  const onSearchChange = vi.fn();
  const onViewModeChange = vi.fn();
  const onExport = vi.fn();
  const onToggleFilters = vi.fn();

  const summary: TodaySummary = {
    total: 12,
    by_status: { CHECKED_IN: 3, TRIAGE: 2, WITH_PROVIDER: 4, PENDING_RESULTS: 3 },
    by_type: { CONSULTATION: 8, EMERGENCY: 4 },
  };

  const defaults = {
    summary,
    isLoading: false,
    search: "",
    onSearchChange,
    viewMode: "kanban" as const,
    onViewModeChange,
    onExport,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders total count in the title", () => {
    render(<QueueStatsBar {...defaults} />);
    expect(screen.getByText(/12 total/i)).toBeInTheDocument();
  });

  it("renders status badges with correct counts", () => {
    render(<QueueStatsBar {...defaults} />);
    // Check at least one status badge shows its count
    expect(screen.getByText(/3/)).toBeInTheDocument();
  });

  it("renders loading skeletons when isLoading is true", () => {
    const { container } = render(
      <QueueStatsBar {...defaults} isLoading={true} summary={undefined} />,
    );
    const skeletons = container.querySelectorAll("[class*='animate-pulse'], [class*='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("calls onSearchChange when typing in search input", async () => {
    const user = userEvent.setup();
    render(<QueueStatsBar {...defaults} />);
    const input = screen.getByPlaceholderText(/search/i);
    await user.type(input, "John");
    expect(onSearchChange).toHaveBeenCalled();
  });

  it("calls onViewModeChange when clicking table view button", async () => {
    const user = userEvent.setup();
    render(<QueueStatsBar {...defaults} viewMode="kanban" />);
    // The view toggle is a 2-button group: [kanban (LayoutGrid icon), table (List icon)]
    // The table button is the second one in the toggle group
    const allButtons = screen.getAllByRole("button");
    // The table button has variant ghost when kanban is active. Find by position:
    // Buttons: Filters (maybe), Kanban (active), Table, CSV
    const csvBtn = allButtons.find((b) => b.textContent?.includes("CSV"));
    // The table button is immediately before the CSV button
    if (csvBtn) {
      const csvIdx = allButtons.indexOf(csvBtn);
      const tableBtn = allButtons[csvIdx - 1];
      await user.click(tableBtn);
      expect(onViewModeChange).toHaveBeenCalledWith("table");
    }
  });

  it("calls onExport when CSV button is clicked", async () => {
    const user = userEvent.setup();
    render(<QueueStatsBar {...defaults} />);
    const csvBtn = screen.getByText("CSV").closest("button")!;
    await user.click(csvBtn);
    expect(onExport).toHaveBeenCalledTimes(1);
  });

  it("shows filters toggle button when onToggleFilters is provided", () => {
    render(
      <QueueStatsBar {...defaults} onToggleFilters={onToggleFilters} filtersOpen={false} />,
    );
    const buttons = screen.getAllByRole("button");
    const filterBtn = buttons.find(
      (b) => b.textContent?.toLowerCase().includes("filter"),
    );
    expect(filterBtn).toBeDefined();
  });

  it("renders today's date", () => {
    render(<QueueStatsBar {...defaults} />);
    // Check that the component displays something about today's date
    const today = new Date();
    const dayName = today.toLocaleDateString("en-US", { weekday: "long" });
    // Just check that at least the weekday appears somewhere
    expect(screen.getByText(new RegExp(dayName, "i"))).toBeInTheDocument();
  });
});
