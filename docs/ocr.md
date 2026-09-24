# Document intelligence pipeline

Uploaded documents start with `ocr_status=PENDING`. The document route dispatches
`app.ocr.pipeline.process_document` to Celery after the upload transaction commits.
The task is idempotent: completed documents are skipped, while retryable failures
are marked `FAILED` before Celery retries with exponential backoff.

`OCR_ENGINE` selects `mock`, `paddleocr`, or `doctr`; `OCR_LANGUAGES` configures
the language list (English and Hindi are the default). The mock engine treats
UTF-8 lines as OCR boxes, which keeps offline tests deterministic.

The pipeline applies image orientation, contrast, and median-filter preprocessing,
then extracts typed fields using document-type-specific regex and layout
heuristics. Each field stores its confidence and source bounding box in
`extracted_fields`. Aadhaar extraction stores only the last four digits.
