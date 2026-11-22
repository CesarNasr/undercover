import { useEffect, useState } from "react";
import { api, type Claim, type Handler } from "./api";

export function Actions({
  claim,
  onChange,
}: Readonly<{ claim: Claim; onChange: (claim: Claim) => void }>) {
  const [handlers, setHandlers] = useState<Handler[]>([]);
  const [handler, setHandler] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void api<Handler[]>("handlers")
      .then((list) => {
        if (active)
          setHandlers(list.filter((item) => item.can_approve_over_limit));
      })
      .catch(() => {
        if (active)
          setError("Could not load handlers. Reopen this claim to retry.");
      });
    return () => {
      active = false;
    };
  }, []);
  async function act(operation: string, body: object) {
    setBusy(true);
    setError("");
    try {
      onChange(await api<Claim>(`claims/${claim.claim_id}/${operation}`, body));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed. Retry.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div>
      {error && <p role="alert">{error}</p>}
      <div className="actions">
        {claim.status === "waiting" && (
          <button
            disabled={busy}
            onClick={() => {
              void act("runs", { thread_id: crypto.randomUUID() });
            }}
          >
            Run agent
          </button>
        )}
        {claim.status === "in_progress" && (
          <p role="status">Agent is working…</p>
        )}
        {claim.status === "waiting_for_sign_off" && !claim.sign_off && (
          <>
            <label htmlFor="handler">Sign off as</label>
            <select
              id="handler"
              value={handler}
              onChange={(event) => {
                setHandler(event.target.value);
              }}
            >
              <option value="">Choose a handler</option>
              {handlers.map((item) => (
                <option key={item.handler_id} value={item.handler_id}>
                  {item.name}
                </option>
              ))}
            </select>
            <button
              disabled={busy || !handler}
              onClick={() => {
                void act("sign-off", { handler_id: handler });
              }}
            >
              Sign off payout
            </button>
          </>
        )}
        {claim.decision?.outcome === "approve" &&
          !claim.payment &&
          (claim.status !== "waiting_for_sign_off" || claim.sign_off) && (
            <button
              disabled={busy}
              onClick={() => {
                void act("payment", { amount: claim.decision?.payout });
              }}
            >
              Record simulated payment
            </button>
          )}
      </div>
    </div>
  );
}
