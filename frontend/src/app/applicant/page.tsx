export default function ApplicantPage() {
  return (
    <section aria-labelledby="applicant-title">
      <div className="mb-8">
        <p className="text-sm font-semibold text-brand">Applicant portal</p>
        <h1 id="applicant-title" className="mt-1 text-3xl font-bold">Your scholarship journey</h1>
        <p className="mt-2 max-w-2xl text-muted">Complete your application, attach documents, and track every review step in one place.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {["Draft applications", "Submitted", "Awards"].map((label, index) => (
          <div className="rounded-xl border border-border bg-white p-5" key={label}>
            <p className="text-sm text-muted">{label}</p><p className="mt-2 text-3xl font-bold">{index === 0 ? "0" : "—"}</p>
          </div>
        ))}
      </div>
      <div className="mt-6 rounded-xl border border-border bg-white p-6">
        <h2 className="text-lg font-bold">Start an application</h2>
        <p className="mt-2 text-sm text-muted">Choose a scholarship scheme to begin. Your progress saves automatically.</p>
        <button className="mt-4 rounded-md bg-brand px-4 py-3 font-bold text-white hover:bg-green-800">Browse schemes</button>
      </div>
    </section>
  );
}
