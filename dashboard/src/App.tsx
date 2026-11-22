import { useEffect, useState } from "react";
import { api, label, money, type Claim } from "./api";
import { ClaimDetail } from "./ClaimDetail";
import "./style.css";

export function App() {
  const [claims, setClaims] = useState<Claim[]>();
  const [selected, setSelected] = useState("");
  const [instructions, setInstructions] = useState<string>();
  const [view, setView] = useState("queue");
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    void Promise.all([api<Claim[]>("claims"), api<string>("instructions")])
      .then(([queue, text]) => {
        if (active) {
          setClaims(queue);
          setInstructions(text);
        }
      })
      .catch((err: unknown) => {
        if (active)
          setError(err instanceof Error ? err.message : "Request failed");
      });
    return () => {
      active = false;
    };
  }, [revision]);
  return (
    <div className="shell">
      <header>
        <a href="#main" className="brand">
          UnderCover<span>Travel insurance</span>
        </a>
        <nav aria-label="Main">
          <button
            onClick={() => {
              setView("queue");
              setSelected("");
              setRevision((value) => value + 1);
            }}
          >
            Claims queue
          </button>
          <button
            onClick={() => {
              setView("instructions");
            }}
          >
            Agent instructions
          </button>
        </nav>
      </header>
      <main id="main">
        {error && (
          <p role="alert">
            {error}{" "}
            <button
              onClick={() => {
                window.location.reload();
              }}
            >
              Reload
            </button>
          </p>
        )}
        {view === "instructions" ? (
          <section>
            <p className="eyebrow">UnderCover Agent</p>
            <h1>Agent instructions</h1>
            <pre>{instructions}</pre>
          </section>
        ) : (
          <>
            {selected ? (
              <>
                <button
                  onClick={() => {
                    setSelected("");
                    setRevision((value) => value + 1);
                  }}
                >
                  Back to queue
                </button>
                <ClaimDetail key={selected} id={selected} />
              </>
            ) : (
              <>
                <div className="intro">
                  <p className="eyebrow">Claims operations</p>
                  <h1>Every claim. A clear decision.</h1>
                  <p>
                    Review the evidence, follow the agent and keep payments
                    under control.
                  </p>
                </div>
                <section>
                  <h2>Claims queue</h2>
                  {claims ? (
                    <>
                      <p>{claims.length} claims</p>
                      {claims.length === 0 && <p>No claims waiting</p>}
                      <div className="queue">
                        {claims.map((claim) => (
                          <button
                            className="claim"
                            key={claim.claim_id}
                            onClick={() => {
                              setSelected(claim.claim_id);
                            }}
                          >
                            <span className="identifier">
                              {claim.claim_id} · {claim.customer_name}
                            </span>
                            <strong>{claim.summary}</strong>
                            <span>{money(claim.amount_claimed)}</span>
                            <span className={`badge ${claim.status}`}>
                              {label(claim.status)}
                            </span>
                          </button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p>Loading queue…</p>
                  )}
                </section>
              </>
            )}
          </>
        )}
      </main>
      <footer>UnderCover claims pilot · Payments are simulated</footer>
    </div>
  );
}
