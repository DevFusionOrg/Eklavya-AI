"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { getOfficerQueue, type QueueItem } from "../../lib/api";

const views = {
  "My scrutiny": { status: "UNDER_SCRUTINY" },
  "Low confidence": { status: "UNDER_SCRUTINY", confidence_band: "LOW" },
  "Deficiencies": { status: "DEFICIENT", deficiency_severity: "HIGH" },
};

export default function OfficerPage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [view, setView] = useState("My scrutiny");
  const [scheme, setScheme] = useState("");
  const [status, setStatus] = useState("UNDER_SCRUTINY");
  const [confidence, setConfidence] = useState("");
  const [severity, setSeverity] = useState("");
  const [saved, setSaved] = useState<string[]>([]);
  const [notice, setNotice] = useState("");

  const load = useCallback(async (filters = views[view as keyof typeof views]) => {
    try {
      const result = await getOfficerQueue({ ...filters, scheme, status, confidence_band: confidence, deficiency_severity: severity });
      setItems(result.items);
      setTotal(result.total);
    } catch {
      setNotice("Queue unavailable. Check your connection and try again.");
    }
  }, [confidence, scheme, severity, status, view]);

  useEffect(() => {
    setSaved(JSON.parse(localStorage.getItem("eklavya.officer.views") ?? "[]") as string[]);
    void load();
  }, [load]);

  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if (event.key === "r" && !["INPUT", "SELECT"].includes(document.activeElement?.tagName ?? "")) {
        event.preventDefault();
        void load();
      }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  });

  function saveView() {
    if (!view.trim()) return;
    const next = Array.from(new Set([...saved, view.trim()]));
    setSaved(next);
    localStorage.setItem("eklavya.officer.views", JSON.stringify(next));
    setNotice("View saved on this device.");
  }

  return (
    <section aria-labelledby="officer-title">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="text-sm font-semibold text-brand">Officer portal</p><h1 id="officer-title" className="mt-1 text-3xl font-bold">Scrutiny queue</h1><p className="mt-2 text-muted">Use R to refresh. Open an application to review evidence in split view.</p></div>
        <button type="button" onClick={() => void load()} className="rounded-md border border-border bg-white px-4 py-3 text-sm font-bold">Refresh queue</button>
      </div>
      {notice && <p role="status" className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-900">{notice}</p>}
      <div className="mb-4 rounded-xl border border-border bg-white p-4">
        <div className="flex flex-wrap gap-2">{Object.keys(views).map((name) => <button type="button" key={name} onClick={() => { setView(name); const filters = views[name as keyof typeof views]; void load(filters); }} className={`rounded-full px-3 py-2 text-sm font-bold ${view === name ? "bg-brand text-white" : "bg-surface text-muted"}`}>{name}</button>)}<button type="button" onClick={saveView} className="rounded-full border border-border px-3 py-2 text-sm font-bold">Save view</button></div>
        {saved.length > 0 && <p className="mt-3 text-xs text-muted">Saved locally: {saved.join(", ")}</p>}
        <div className="mt-4 grid gap-3 sm:grid-cols-4">
          <label className="text-sm font-semibold">Scheme<input value={scheme} onChange={(event) => setScheme(event.target.value)} placeholder="All schemes" className="mt-1 w-full rounded-md border border-border px-3 py-2" /></label>
          <label className="text-sm font-semibold">Status<select value={status} onChange={(event) => setStatus(event.target.value)} className="mt-1 w-full rounded-md border border-border px-3 py-2"><option>UNDER_SCRUTINY</option><option>DEFICIENT</option><option>OFFICER_VERIFIED</option></select></label>
          <label className="text-sm font-semibold">Confidence<select value={confidence} onChange={(event) => setConfidence(event.target.value)} className="mt-1 w-full rounded-md border border-border px-3 py-2"><option value="">Any confidence</option><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option></select></label>
          <label className="text-sm font-semibold">Deficiency<select value={severity} onChange={(event) => setSeverity(event.target.value)} className="mt-1 w-full rounded-md border border-border px-3 py-2"><option value="">Any severity</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label>
        </div>
        <button type="button" onClick={() => void load()} className="mt-4 rounded-md bg-brand px-4 py-2 text-sm font-bold text-white">Apply filters</button>
      </div>
      <div className="overflow-hidden rounded-xl border border-border bg-white">
        <div className="border-b border-border p-4"><h2 className="font-bold">Applications requiring attention <span className="ml-2 text-sm font-normal text-muted">{total} total</span></h2></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><caption className="sr-only">Officer scrutiny queue</caption><thead className="bg-surface text-xs uppercase text-muted"><tr><th className="px-4 py-3">Application</th><th className="px-4 py-3">Scheme</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Assignment</th><th className="px-4 py-3">Action</th></tr></thead><tbody>{items.map((item) => <tr className="border-t border-border" key={item.id}><td className="px-4 py-4 font-mono text-xs">{item.id.slice(0, 8).toUpperCase()}</td><td className="px-4 py-4 font-semibold">{item.scheme}</td><td className="px-4 py-4">{item.status.replaceAll("_", " ")}</td><td className="px-4 py-4 text-xs text-muted">{item.scrutiny_officer_id ? "Claimed" : "Unassigned"}</td><td className="px-4 py-4"><Link className="rounded-md bg-brand px-3 py-2 font-bold text-white" href={`/officer/review/${item.id}`}>Review</Link></td></tr>)}{!items.length && <tr><td className="px-4 py-8 text-muted" colSpan={5}>No applications match these filters.</td></tr>}</tbody></table></div>
      </div>
    </section>
  );
}
