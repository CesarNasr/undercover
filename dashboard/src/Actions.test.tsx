import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Actions } from "./Actions";
import type { Claim } from "./api";

const claim: Claim = {
  claim_id: "CLM-1001",
  customer_id: "CUS-3001",
  customer_name: "Maya Patel",
  policy_id: "POL-2001",
  summary: "Delay",
  amount_claimed: 1250,
  status: "waiting_for_sign_off",
  decision: {
    outcome: "approve",
    payout: "1250",
    calculation: "Costs",
    explanation: "Covered.",
    policy_references: ["3"],
  },
  sign_off: null,
  payment: null,
  events: [],
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("signs off with the chosen eligible handler", async () => {
  const changed = vi.fn();
  const fetcher = vi.fn((url: string) =>
    Promise.resolve(
      new Response(
        JSON.stringify(
          url.endsWith("handlers")
            ? [
                {
                  handler_id: "HND-01",
                  name: "Dana",
                  can_approve_over_limit: true,
                },
              ]
            : claim,
        ),
      ),
    ),
  );
  vi.stubGlobal("fetch", fetcher);
  render(<Actions claim={claim} onChange={changed} />);
  await screen.findByRole("option", { name: "Dana" });
  fireEvent.change(screen.getByLabelText("Sign off as"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(screen.getByText("Sign off payout"));
  await waitFor(() => {
    expect(changed).toHaveBeenCalledWith(claim);
  });
  expect(fetcher).toHaveBeenLastCalledWith(
    "/api/claims/CLM-1001/sign-off",
    expect.objectContaining({ body: '{"handler_id":"HND-01"}' }),
  );
});
it("preserves approval and allows payment retry after an error", async () => {
  const changed = vi.fn();
  const fetcher = vi.fn((url: string) =>
    url.endsWith("handlers")
      ? Promise.resolve(new Response("[]"))
      : Promise.resolve(new Response("{}", { status: 409 })),
  );
  vi.stubGlobal("fetch", fetcher);
  render(
    <Actions
      claim={{
        ...claim,
        sign_off: { handler_id: "HND-01", timestamp: "today" },
      }}
      onChange={changed}
    />,
  );
  fireEvent.click(screen.getByText("Record simulated payment"));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Request failed (409). Please retry.",
  );
  expect(changed).not.toHaveBeenCalled();
  fetcher.mockImplementation(() =>
    Promise.resolve(new Response(JSON.stringify(claim))),
  );
  fireEvent.click(screen.getByText("Record simulated payment"));
  await waitFor(() => {
    expect(changed).toHaveBeenCalled();
  });
});
it("reports unavailable handler records", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  render(<Actions claim={claim} onChange={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Could not load handlers. Reopen this claim to retry.",
  );
});
