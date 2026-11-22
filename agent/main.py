"""The UnderCover Agent."""

import os

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

BACKEND_URL = "http://localhost:8000"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=os.getenv("BACKEND_URL", BACKEND_URL), timeout=10)


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim and return its final reply."""

    def request(method: str, path: str, body: dict[str, object]) -> str:
        with backend() as client:
            response = client.request(
                method, path, json=body if method == "POST" else None
            )
        if response.is_error:
            return f"Request blocked: {response.status_code} {response.text}"
        return response.text

    def log(message: str) -> None:
        request(
            "POST",
            f"/api/claims/{claim_id}/events",
            {"thread_id": thread_id, "message": message},
        )

    @tool
    def read_context() -> str:
        """Read the assigned claim, policy, customer history, plans and wording."""
        log("Reading claim and policy context")
        with backend() as client:
            response = client.get(f"/api/claims/{claim_id}")
            response.raise_for_status()
            claim = response.json()
        paths = [
            f"/api/policies/{claim['policy_id']}",
            f"/api/customers/{claim['customer_id']}",
            "/api/plans",
            "/api/policy-wording",
        ]
        return (
            response.text + "\n" + "\n".join(request("GET", path, {}) for path in paths)
        )

    @tool
    def record_decision(
        outcome: str,
        payout: str,
        calculation: str,
        explanation: str,
        policy_references: list[str],
    ) -> str:
        """Record approve, decline or refer with USD payout and policy references."""
        log("Recording coverage decision")
        return request(
            "POST",
            f"/api/claims/{claim_id}/decision",
            {
                "outcome": outcome,
                "payout": payout,
                "calculation": calculation,
                "explanation": explanation,
                "policy_references": policy_references,
                "thread_id": thread_id,
            },
        )

    @tool
    def request_payment(amount: str) -> str:
        """Request the exact approved USD payout, subject to handler sign-off."""
        log("Requesting simulated payment")
        return request("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})

    with backend() as client:
        response = client.get("/api/instructions")
        response.raise_for_status()
        instructions = response.json()
    agent = create_agent(
        llm or model(),
        tools=[read_context, record_decision, request_payment],
        system_prompt=instructions,
    )
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Process claim {claim_id}. Read context first, "
                    "then record your decision and request payment if approved.",
                }
            ]
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].text
