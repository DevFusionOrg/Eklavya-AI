# Load test

The Locust scenario in `locustfile.py` measures draft creation, autosave,
submission, and document upload that enqueues OCR. It reports request
throughput, p50/p95 latency, and failures in Locust CSV output.

Example (with a seeded applicant and published scheme version):

```bash
LOCUST_SCHEME_VERSION_ID=<uuid> \
locust -f loadtest/locustfile.py --host http://localhost:8000 \
  --headless -u 20 -r 5 -t 60s --csv loadtest/results
```

For a meaningful baseline, run against the Docker stack with seeded test
accounts and record the generated `*_stats.csv` artifact. Report separately:

- API submit throughput: successful `applications/submit` requests/second.
- OCR enqueue throughput: successful `documents/upload-enqueue-ocr` requests/second.
- API latency: p50 and p95 from Locust.
- Worker throughput: completed OCR tasks/minute from Celery metrics.

No production capacity target is asserted by this repository; hardware,
document size, database, and worker concurrency must be recorded with each
benchmark.
