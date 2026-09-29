import { expect, type Page, test } from "@playwright/test";

function tokenFor(role: string) {
  return `header.${btoa(JSON.stringify({ sub: "123", role })).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "")}.signature`;
}

function jsonRoute(
  body: unknown,
  status = 200,
): { status: number; contentType: string; body: string } {
  return { status, contentType: "application/json", body: JSON.stringify(body) };
}

async function mockApplicantApi(page: Page) {
  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill(jsonRoute({ access_token: tokenFor("APPLICANT"), refresh_token: tokenFor("APPLICANT"), token_type: "bearer" })),
  );
  await page.route("**/api/v1/schemes", (route) =>
    route.fulfill(jsonRoute([{ id: "scheme-1", code: "ST-2026", name: "ST Scholarship", description: "Demo", is_active: true }])),
  );
  await page.route("**/api/v1/applications", (route) =>
    route.fulfill(jsonRoute([{ id: "application-1", status: "DEFICIENT", scheme_code: "ST-2026", scheme_name: "ST Scholarship", correction_round: 1, correction_deadline: "2099-01-01T00:00:00Z", form_data: {} }])),
  );
  await page.route("**/api/v1/applications/application-1/timeline", (route) =>
    route.fulfill(jsonRoute([{ from_status: "SUBMITTED", to_status: "DEFICIENT", reason: "Missing document", created_at: "2026-01-01T00:00:00Z" }])),
  );
  await page.route("**/api/v1/applications/application-1/deficiencies", (route) =>
    route.fulfill(jsonRoute({ repeat_deficiency_cycles: 1, correction_round: 1, correction_deadline: "2099-01-01T00:00:00Z", items: [{ id: "def-1", code: "MISSING_DOC", message: "Upload your caste certificate", field: null, document_id: null, severity: "HIGH", status: "OPEN" }] })),
  );
  await page.route("**/api/v1/notifications/preferences", (route) => route.fulfill(jsonRoute({ locale: "en", sms_enabled: true, email_enabled: true, in_app_enabled: true })));
  await page.route("**/api/v1/followups/mine", (route) => route.fulfill(jsonRoute([])));
}

async function signIn(page: Page, email = "applicant@example.test") {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("Strong-password-123!");
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("golden path: apply, deficiency, and resubmit", async ({ page }) => {
  await mockApplicantApi(page);
  await signIn(page);
  await expect(page).toHaveURL(/\/applicant$/);
  await expect(page.getByText("Action needed")).toBeVisible();
  await expect(page.getByText("Upload your caste certificate")).toBeVisible();
  await page.getByRole("link", { name: "Fix this" }).click();
  await expect(page).toHaveURL(/\/applicant\/apply\/ST-2026/);
});

test("golden path: officer verifies and selection workspace is reachable", async ({ page }) => {
  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill(jsonRoute({ access_token: tokenFor("SCRUTINY_OFFICER"), refresh_token: tokenFor("SCRUTINY_OFFICER"), token_type: "bearer" })),
  );
  await page.route("**/api/v1/officer/queue**", (route) =>
    route.fulfill(jsonRoute({ items: [{ id: "application-1", scheme: "ST-2026", status: "UNDER_SCRUTINY", scrutiny_officer_id: null, verifying_officer_id: null }], total: 1 })),
  );
  await page.goto("/login");
  await page.getByLabel("Email").fill("officer@example.test");
  await page.getByLabel("Password").fill("Strong-password-123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/officer$/);
  await expect(page.getByText("Applications requiring attention")).toBeVisible();
  await page.getByRole("link", { name: "Review" }).click();
  await expect(page).toHaveURL(/\/officer\/review\/application-1/);
});

test("golden path: awarded applicant sees follow-up workspace", async ({ page }) => {
  await mockApplicantApi(page);
  await page.route("**/api/v1/applications", (route) =>
    route.fulfill(jsonRoute([{ id: "application-2", status: "AWARDED", scheme_code: "ST-2026", scheme_name: "ST Scholarship", correction_round: 0, correction_deadline: null, form_data: {} }])),
  );
  await page.route("**/api/v1/applications/application-2/timeline", (route) => route.fulfill(jsonRoute([])));
  await page.route("**/api/v1/applications/application-2/deficiencies", (route) => route.fulfill(jsonRoute({ repeat_deficiency_cycles: 0, correction_round: 0, correction_deadline: null, items: [] })));
  await page.route("**/api/v1/followups/mine", (route) =>
    route.fulfill(jsonRoute([{ id: "award-1", application_id: "application-2", amount: "1000", status: "ACTIVE", instalments: [], requirements: [{ id: "req-1", name: "Semester marksheet", status: "UPCOMING", due_date: "2099-06-01T00:00:00Z" }] }])),
  );
  await signIn(page);
  await expect(page.getByText("Awards")).toBeVisible();
  await expect(page.getByText("Semester marksheet")).toBeVisible();
});
