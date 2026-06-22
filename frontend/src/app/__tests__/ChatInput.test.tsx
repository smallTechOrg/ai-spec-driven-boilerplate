import { render, screen } from "@testing-library/react";
import { ChatInput } from "../components/ChatInput";

describe("ChatInput", () => {
  it("submit button is disabled when hasDatasets is false", () => {
    render(<ChatInput hasDatasets={false} isQuerying={false} onSubmit={() => {}} />);
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("submit button is disabled while querying", () => {
    render(<ChatInput hasDatasets={true} isQuerying={true} onSubmit={() => {}} />);
    expect(screen.getByRole("button", { name: /…/i })).toBeDisabled();
  });

  it("textarea is disabled when hasDatasets is false", () => {
    render(<ChatInput hasDatasets={false} isQuerying={false} onSubmit={() => {}} />);
    expect(screen.getByRole("textbox")).toBeDisabled();
  });
});
