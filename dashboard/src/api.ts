export type Value =
  string | number | boolean | null | Value[] | { [key: string]: Value };
export interface Claim {
  claim_id: string;
  customer_id: string;
  customer_name: string;
  policy_id: string;
  summary: string;
  amount_claimed: number;
  status: string;
  decision: {
    outcome: string;
    payout: string;
    calculation: string;
    explanation: string;
    policy_references: string[];
  } | null;
  payment: { amount: string; timestamp: string } | null;
  sign_off: { handler_id: string; timestamp: string } | null;
  events: { timestamp: string; thread_id: string; message: string }[];
}
export interface Handler {
  handler_id: string;
  name: string;
  can_approve_over_limit: boolean;
}
export const money = (amount: number | string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    Number(amount),
  );
export const label = (text: string) => text.replaceAll("_", " ");
export async function api<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(
    `/api/${path}`,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined,
  );
  if (!response.ok)
    throw new Error(
      `Request failed (${String(response.status)}). Please retry.`,
    );
  return response.json() as Promise<T>;
}
