import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { RecordView } from "./RecordView";
import { api, type Claim } from "./api";

const claim: Claim = {
  claim_id: "CLM-1001",
  customer_id: "CUS-3001",
  customer_name: "Maya Patel",
  policy_id: "POL-2001",
  summary: "Flight canceled",
  amount_claimed: 1250,
  status: "waiting",
  decision: null,
  payment: null,
  sign_off: null,
  events: [],
};
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
function mock(data: Claim[] = [claim]) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      let result: unknown = {};
      if (url === "/api/claims") result = data;
      else if (url === "/api/instructions") result = "Read policy wording";
      else if (url === "/api/policy-wording")
        result = "Policy contract version 2026.1";
      else if (url.includes("/claims/")) result = data[0];
      else if (url === "/api/handlers")
        result = [
          { handler_id: "HND-01", name: "Dana", can_approve_over_limit: true },
        ];
      return Promise.resolve(new Response(JSON.stringify(result)));
    }),
  );
}
it("loads the queue, full claim and instructions", async () => {
  mock();
  render(<App />);
  expect(screen.getByText("Loading queue…")).toBeDefined();
  fireEvent.click(await screen.findByText("Flight canceled"));
  expect(await screen.findByText("Awaiting processing")).toBeDefined();
  expect(screen.getByText("No activity yet")).toBeDefined();
  fireEvent.click(screen.getByText("Back to queue"));
  expect(await screen.findByText("Flight canceled")).toBeDefined();
  fireEvent.click(screen.getByText("Agent instructions"));
  expect(screen.getByText("Read policy wording")).toBeDefined();
  expect(
    screen.getByRole("heading", {
      name: "What the agent reads before deciding a claim",
    }),
  ).toBeDefined();
  expect(screen.getByText("The customer’s history:")).toBeDefined();
  expect(screen.getByText("Policy contract version 2026.1")).toBeDefined();
  expect(screen.queryByRole("textbox")).toBeNull();
  fireEvent.click(screen.getByText("Claims queue"));
  expect(screen.getByText("Flight canceled")).toBeDefined();
});
it("shows a stored decision, sign-off, payment and activity", async () => {
  mock([
    {
      ...claim,
      status: "decided",
      decision: {
        outcome: "approve",
        payout: "1250",
        calculation: "Eligible costs",
        explanation: "Covered delay.",
        policy_references: ["3"],
      },
      sign_off: { handler_id: "HND-01", timestamp: "today" },
      payment: { amount: "1250", timestamp: "today" },
      events: [
        {
          message: "Payment recorded",
          timestamp: "2026-01-01",
          thread_id: "one",
        },
      ],
    },
  ]);
  render(<App />);
  fireEvent.click(await screen.findByText("Flight canceled"));
  expect(await screen.findAllByText("Covered delay.")).toBeDefined();
  expect(screen.getByText("Simulated payment: $1,250.00")).toBeDefined();
});
it("handles an empty queue", async () => {
  mock([]);
  render(<App />);
  expect(await screen.findByText("No claims waiting")).toBeDefined();
});
it("shows request errors", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Offline")));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Offline Reload",
  );
});
it("shows claim loading errors", async () => {
  mock();
  render(<App />);
  const button = await screen.findByText("Flight canceled");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new Error("Claim unavailable")),
  );
  fireEvent.click(button);
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Claim unavailable",
  );
});
it("renders nested record values", () => {
  render(<RecordView value={{ example: [null, true, 5, "text"] }} />);
  expect(screen.getByText("None")).toBeDefined();
});
it("rejects unsuccessful API calls", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("{}", { status: 409 })),
  );
  await expect(api("claims", {})).rejects.toThrow("409");
});

it("starts a run and displays progress until completion", async () => {
  let current = { ...claim };
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, options?: RequestInit) => {
      let result: unknown = {};
      if (url === "/api/claims") result = [current];
      else if (url === "/api/instructions") result = "Instructions";
      else if (url.endsWith("/runs") && options) {
        current = { ...current, status: "in_progress" };
        result = current;
      } else if (url.includes("/claims/")) result = current;
      else if (url === "/api/handlers") result = [];
      return Promise.resolve(new Response(JSON.stringify(result)));
    }),
  );
  render(<App />);
  fireEvent.click(await screen.findByText("Flight canceled"));
  fireEvent.click(await screen.findByRole("button", { name: "Run agent" }));
  expect(await screen.findByRole("status")).toHaveProperty(
    "textContent",
    "Agent is working…",
  );
  current = { ...current, status: "decided" };
  await screen.findAllByText("decided");
  cleanup();
});
