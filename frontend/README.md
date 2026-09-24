# Eklavya.AI frontend

The Next.js App Router frontend provides accessible Applicant and Officer
shells, role-aware middleware, low-bandwidth responsive layouts, and a typed
API boundary. Authentication stores short-lived tokens in the browser and
mirrors only the role in a SameSite cookie for middleware routing.

Run locally:

```powershell
npm install
npm run dev
```

When the backend is running, refresh the generated OpenAPI types with:

```powershell
npm run generate:api
```

English and Hindi message catalogs live in `src/i18n/messages`; additional
regional languages can be added without changing the shell structure.
