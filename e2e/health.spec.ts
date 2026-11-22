import { expect, test } from "@playwright/test";

test("handlers can inspect the queue, claim and read-only instructions", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.getByText("25 claims")).toBeVisible();
  await page.screenshot({ path: "e2e/test-results/queue.png", fullPage: true });
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toBeVisible();
  await page.getByRole("button", { name: /CLM-1001/ }).click();
  await expect(page.getByText("Awaiting processing")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Policy and customer" }),
  ).toBeVisible();
  await page.screenshot({ path: "e2e/test-results/claim.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "e2e/test-results/mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Agent instructions" }).click();
  await expect(
    page.getByText("You are the UnderCover Agent.", { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
});

for (const [id, outcome] of [
  ["CLM-1001", "approve"],
  ["CLM-1003", "decline"],
  ["CLM-1004", "refer"],
]) {
  test(`process ${id} as ${outcome}`, async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: new RegExp(id) }).click();
    await page.getByRole("button", { name: "Run agent" }).click();
    await expect(page.getByRole("status")).toHaveText("Agent is working…");
    await expect(
      page.getByRole("heading", { name: new RegExp(`^${outcome}`) }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Back to queue" }).click();
    await page.getByRole("button", { name: new RegExp(id) }).click();
    await expect(
      page.getByRole("heading", { name: new RegExp(`^${outcome}`) }),
    ).toBeVisible();
    await page.screenshot({ path: `e2e/test-results/${id}.png` });
  });
}

test("over-limit approval waits for sign-off and payment survives reload", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: /CLM-1002/ }).click();
  await page.getByRole("button", { name: "Run agent" }).click();
  await expect(page.getByRole("status")).toHaveText("Agent is working…");
  await expect(page.getByRole("heading", { name: /^approve/ })).toBeVisible();
  const blocked = await request.post(
    "http://localhost:8000/api/claims/CLM-1002/payment",
    { data: { amount: "1250" } },
  );
  expect(blocked.status()).toBe(409);
  await expect(page.getByText("No payment recorded")).toBeVisible();
  await page.getByLabel("Sign off as").selectOption("HND-01");
  await page.getByRole("button", { name: "Sign off payout" }).click();
  await page.getByRole("button", { name: "Record simulated payment" }).click();
  await expect(page.getByText("Simulated payment: $1,250.00")).toBeVisible();

  await page.reload();
  await page.getByRole("button", { name: /CLM-1002/ }).click();
  await expect(page.getByText("Simulated payment: $1,250.00")).toBeVisible();
  await page.screenshot({ path: "e2e/test-results/sign-off.png" });
});
