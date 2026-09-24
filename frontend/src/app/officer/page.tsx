export default function OfficerPage() {
  return (
    <section aria-labelledby="officer-title">
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="text-sm font-semibold text-brand">Officer portal</p><h1 id="officer-title" className="mt-1 text-3xl font-bold">Scrutiny queue</h1><p className="mt-2 text-muted">Review applications with evidence, rules, and AI assistance side by side.</p></div>
        <button className="rounded-md border border-border bg-white px-4 py-3 text-sm font-bold hover:bg-surface">Export queue</button>
      </div>
      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        {["Awaiting review", "Low confidence", "Deficient", "Verified today"].map((label) => <div className="rounded-lg border border-border bg-white p-4" key={label}><p className="text-xs uppercase tracking-wide text-muted">{label}</p><p className="mt-2 text-2xl font-bold">—</p></div>)}
      </div>
      <div className="overflow-hidden rounded-xl border border-border bg-white">
        <div className="border-b border-border p-4"><h2 className="font-bold">Applications requiring attention</h2></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-left text-sm"><caption className="sr-only">Officer scrutiny queue</caption><thead className="bg-surface text-xs uppercase text-muted"><tr><th className="px-4 py-3">Application</th><th className="px-4 py-3">Scheme</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Action</th></tr></thead><tbody><tr><td className="px-4 py-6 text-muted" colSpan={4}>No applications are currently assigned.</td></tr></tbody></table></div>
      </div>
    </section>
  );
}
