import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ResultTable } from "../components/ResultTable";

const makeRows = (n: number): (string | number | null)[][] =>
  Array.from({ length: n }, (_, i) => [`row-${i}`, i]);

describe("ResultTable", () => {
  it("renders column headers", () => {
    render(<ResultTable columns={["name", "count"]} rows={makeRows(3)} />);
    expect(screen.getByText("name")).toBeInTheDocument();
    expect(screen.getByText("count")).toBeInTheDocument();
  });

  it("shows page 1 rows and Previous is disabled", () => {
    render(<ResultTable columns={["x"]} rows={makeRows(30)} />);
    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
  });

  it("Next navigates to page 2", async () => {
    const user = userEvent.setup();
    render(<ResultTable columns={["x"]} rows={makeRows(30)} />);
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
  });
});
