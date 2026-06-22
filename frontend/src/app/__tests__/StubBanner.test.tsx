import { render, screen } from "@testing-library/react";
import { StubBanner } from "../components/StubBanner";

describe("StubBanner", () => {
  it("renders the amber banner when stubMode is true", () => {
    render(<StubBanner stubMode={true} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Gemini API key not configured/i)).toBeInTheDocument();
  });

  it("renders nothing when stubMode is false", () => {
    const { container } = render(<StubBanner stubMode={false} />);
    expect(container.firstChild).toBeNull();
  });
});
