export function AgentInstructions({
  instructions,
  wording,
}: Readonly<{
  instructions: string | undefined;
  wording: string | undefined;
}>) {
  return (
    <>
      <section>
        <p className="eyebrow">UnderCover Agent</p>
        <h1>Agent instructions</h1>
        <h2>What the agent reads before deciding a claim</h2>
        <p>
          The agent first reads its instructions, then gathers the following
          records for the selected claim:
        </p>
        <ul>
          <li>
            <strong>The claim:</strong> the customer’s account of what happened,
            incident and submission dates, amounts claimed, itemized expenses
            and supporting documents.
          </li>
          <li>
            <strong>The customer’s policy:</strong> the plan, add-ons, purchase
            date, covered trip dates, trip cost and named travelers.
          </li>
          <li>
            <strong>The customer’s history:</strong> previous claims and their
            recorded outcomes.
          </li>
          <li>
            <strong>Plan details:</strong> benefit limits, waiting periods,
            deductibles and add-on coverage.
          </li>
          <li>
            <strong>The policy wording:</strong> the coverage rules, exclusions,
            evidence requirements and payment calculation below.
          </li>
        </ul>
        <p>
          It uses these records to approve, decline or refer the claim,
          calculate any payout and explain its decision with relevant policy
          sections. A payout over $1,000 waits for handler sign-off.
        </p>
        <h2>Instructions used by the agent</h2>
        <pre>{instructions}</pre>
      </section>
      <section>
        <h2>Policy wording</h2>
        <p>
          This is the policy wording the agent reads when assessing a claim.
        </p>
        <pre>{wording}</pre>
      </section>
    </>
  );
}
