"""Load test for application submission and OCR queue enqueueing.

Run against a seeded local stack:
  locust -f loadtest/locustfile.py --host http://localhost:8000 \
    --headless -u 20 -r 5 -t 60s --csv loadtest/results

The scenario measures API latency and failure rate for submission plus document
upload/enqueue. It does not wait for OCR completion because queue throughput
and worker throughput must be reported separately in production.
"""

import os
import uuid

from locust import HttpUser, between, task


class SubmitAndOcrUser(HttpUser):
    wait_time = between(0.2, 1.0)
    applicant_email = os.getenv("LOCUST_APPLICANT_EMAIL", "load@example.test")
    password = os.getenv("LOCUST_APPLICANT_PASSWORD", "Strong-password-123!")

    def on_start(self) -> None:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": self.applicant_email, "password": self.password},
            name="auth/login",
        )
        response.raise_for_status()
        self.client.headers.update(
            {"Authorization": f"Bearer {response.json()['access_token']}"}
        )
        self.scheme_version_id = os.environ.get("LOCUST_SCHEME_VERSION_ID")
        if not self.scheme_version_id:
            raise RuntimeError("LOCUST_SCHEME_VERSION_ID must reference a seeded draft scheme version")

    @task
    def submit_and_enqueue_ocr(self) -> None:
        draft = self.client.post(
            "/api/v1/applications",
            json={"scheme_version_id": self.scheme_version_id, "form_data": {}},
            name="applications/create-draft",
        )
        if draft.status_code not in {200, 201}:
            draft.raise_for_status()
        application_id = draft.json()["id"]
        self.client.patch(
            f"/api/v1/applications/{application_id}",
            json={"form_data": {}},
            name="applications/autosave",
        ).raise_for_status()
        self.client.post(
            f"/api/v1/applications/{application_id}/submit",
            name="applications/submit",
        ).raise_for_status()
        self.client.post(
            f"/api/v1/applications/{application_id}/documents",
            params={"doc_type": "caste_certificate"},
            files={"file": ("fixture.pdf", b"%PDF-1.4\nmock", "application/pdf")},
            name="documents/upload-enqueue-ocr",
        )

        # Avoid accidental correlation of generated IDs with user data in logs.
        assert uuid.UUID(application_id)
