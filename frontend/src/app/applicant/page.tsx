import Link from "next/link";
import { listSchemes } from "../../lib/api";

export default async function ApplicantPage() {
  const schemes = await listSchemes().catch(() => []);
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
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {schemes.filter((scheme) => scheme.is_active).map((scheme) => (
            <Link href={`/applicant/apply/${scheme.code}`} className="rounded-lg border border-border p-4 hover:border-brand hover:bg-green-50" key={scheme.id}>
              <span className="font-bold">{scheme.name}</span>
              <span className="mt-1 block text-sm text-muted">{scheme.description ?? "Open the dynamic application form."}</span>
            </Link>
          ))}
          {!schemes.length && <p className="text-sm text-muted">No schemes are open right now.</p>}
        </div>
      </div>
    </section>
  );
}
