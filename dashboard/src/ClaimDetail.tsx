import { useEffect, useState } from "react";
import { api, label, money, type Claim, type Value } from "./api";
import { Actions } from "./Actions";
import { RecordView } from "./RecordView";

export function ClaimDetail({ id }: Readonly<{ id: string }>) {
  const [claim, setClaim] = useState<Claim>();
  const [context, setContext] = useState<Value>();
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void api<Claim>(`claims/${id}`)
      .then(async (data) => {
        const [policy, customer, plans] = await Promise.all([
          api<Value>(`policies/${data.policy_id}`),
          api<Value>(`customers/${data.customer_id}`),
          api<Value>("plans"),
        ]);
        if (active) {
          setClaim(data);
          setContext({ policy, customer, plans });
        }
      })
      .catch((err: unknown) => {
        if (active)
          setError(err instanceof Error ? err.message : "Request failed");
      });
    return () => {
      active = false;
    };
  }, [id]);
  const running = claim?.status === "in_progress";
  useEffect(() => {
    if (!running) return;
    let active = true;
    const timer = window.setInterval(() => {
      void api<Claim>(`claims/${id}`)
        .then((data) => {
          if (active) setClaim(data);
        })
        .catch(() => {
          if (active)
            setError("Progress unavailable. Reopen the claim to retry.");
        });
    }, 500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [id, running]);
  if (error && !claim) return <p role="alert">{error}</p>;
  if (!claim) return <p>Loading claim…</p>;
  return (
    <>
      {error && <p role="alert">{error}</p>}
      <section>
        <p className="eyebrow">{claim.claim_id}</p>
        <h2>{claim.summary}</h2>
        <p>
          <span className={`badge ${claim.status}`}>{label(claim.status)}</span>{" "}
          · {money(claim.amount_claimed)} claimed
        </p>
      </section>
      <section>
        <Actions claim={claim} onChange={setClaim} />
        <h2>Decision</h2>
        {claim.decision ? (
          <>
            <h3>
              {label(claim.decision.outcome)} · {money(claim.decision.payout)}
            </h3>
            <p>{claim.decision.explanation}</p>
            <p>{claim.decision.calculation}</p>
            <p>
              Policy sections: {claim.decision.policy_references.join(", ")}
            </p>
          </>
        ) : (
          <p>Awaiting processing</p>
        )}
        <p>
          {claim.payment
            ? `Simulated payment: ${money(claim.payment.amount)}`
            : "No payment recorded"}
        </p>
        {claim.sign_off && (
          <p>
            Signed off by {claim.sign_off.handler_id} at{" "}
            {claim.sign_off.timestamp}
          </p>
        )}
      </section>
      <section>
        <h2>Activity</h2>
        {claim.events.length ? (
          <ol>
            {claim.events.map((event, i) => (
              <li key={i}>
                <time>{new Date(event.timestamp).toLocaleTimeString()}</time>{" "}
                {event.message}
              </li>
            ))}
          </ol>
        ) : (
          <p>No activity yet</p>
        )}
      </section>
      <section>
        <h2>Claim record</h2>
        <RecordView
          value={Object.fromEntries(
            Object.entries(claim).filter(
              ([key]) =>
                ![
                  "decision",
                  "payment",
                  "sign_off",
                  "thread_id",
                  "events",
                ].includes(key),
            ),
          )}
        />
      </section>
      <section>
        <h2>Policy and customer</h2>
        {context && <RecordView value={context} />}
      </section>
    </>
  );
}
