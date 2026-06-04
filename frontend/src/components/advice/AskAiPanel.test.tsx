import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../test/test-utils";
import { AskAiPanel } from "./AskAiPanel";

describe("AskAiPanel", () => {
  it("submits a trimmed request payload", () => {
    const onSubmit = vi.fn();

    renderWithProviders(<AskAiPanel onSubmit={onSubmit} />);

    fireEvent.change(
      screen.getByPlaceholderText("Ask about today's fruit, meals, or what to buy next."),
      { target: { value: "  What should I eat first?  " } },
    );
    fireEvent.change(screen.getByPlaceholderText("Optional search context"), {
      target: { value: "  low sugar breakfast  " },
    });
    fireEvent.click(screen.getByLabelText(/more careful reasoning/i));
    fireEvent.click(screen.getByRole("button", { name: /send advice request/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      question: "What should I eat first?",
      search_query: "low sugar breakfast",
      enable_thinking: true,
    });
  });

  it("shows fallback copy and validation errors when accepted is false", () => {
    renderWithProviders(
      <AskAiPanel
        onSubmit={vi.fn()}
        result={{
          accepted: false,
          errors: ["Profile is incomplete.", "Inventory has no confirmed fruit."],
          advice: {
            summary: "Use confirmed inventory as the source of truth.",
            recommendations: [],
            fallback: true,
          },
        }}
      />,
    );

    expect(screen.getByText(/not fully accepted/i)).toBeTruthy();
    expect(screen.getByText("Profile is incomplete.")).toBeTruthy();
    expect(screen.getByText("Inventory has no confirmed fruit.")).toBeTruthy();
    expect(screen.getByText("Use confirmed inventory as the source of truth.")).toBeTruthy();
  });
});
