# Notification delivery

`NotificationService` renders the `deficiency`, `selection`, and `followup`
templates in English or Hindi. The user's preference selects the locale and
enables or disables SMS, email, and in-app channels. Preferences are managed
with:

- `GET/PATCH /api/v1/notifications/preferences`
- `GET /api/v1/notifications/history`

The default console drivers are safe for local development. Set
`EMAIL_DRIVER=smtp` for SMTP email and `SMS_DRIVER=http` for a generic JSON
HTTP SMS provider. Provider failures remain in notification history with
`FAILED`, retry count, and the last error. Celery retries failed deliveries
every five minutes up to `NOTIFICATION_MAX_RETRIES`.

SMS templates intentionally contain only the applicant's name, the short
application reference, and a generic instruction to sign in. Detailed
deficiency, selection, and follow-up information is sent through the portal or
email instead.
