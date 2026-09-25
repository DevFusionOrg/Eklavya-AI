"use client";

import { useEffect, useState } from "react";
import { listFollowupReviews, reviewFollowup, type FollowupReviewItem } from "../lib/api";

export default function FollowupReview() {
  const [items, setItems] = useState<FollowupReviewItem[]>([]);
  const [remarks, setRemarks] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState("");

  async function load() {
    try { setItems(await listFollowupReviews()); }
    catch { setNotice("Follow-up review queue is unavailable."); }
  }
  useEffect(() => { void load(); }, []);

  async function decide(item: FollowupReviewItem, status: "ACCEPTED" | "REJECTED") {
    const text = remarks[item.id]?.trim();
    if (!text) {
      setNotice("Add remarks before reviewing a submission.");
      return;
    }
    try {
      await reviewFollowup(item.id, status, text);
      setNotice(`Submission ${status.toLowerCase()}.`);
      await load();
    } catch { setNotice("Could not record the review."); }
  }

  if (!items.length && !notice) return null;
  return (
    <section className="mt-6 rounded-xl border border-border bg-white p-5" aria-labelledby="followup-review-title">
      <h2 id="followup-review-title" className="text-lg font-bold">Follow-up submissions</h2>
      <p className="mt-1 text-sm text-muted">Review awarded-applicant progress documents and responses.</p>
      {notice && <p role="status" className="mt-3 rounded-md bg-green-50 p-3 text-sm text-green-900">{notice}</p>}
      <div className="mt-4 space-y-3">{items.map((item) => <article className="rounded-lg border border-border p-4" key={item.id}><div className="flex flex-wrap justify-between gap-2"><div><h3 className="font-bold">{item.requirement}</h3><p className="text-xs text-muted">Application {item.application_id.slice(0, 8).toUpperCase()}</p></div>{item.document_id && <span className="text-xs font-semibold text-brand">Document attached</span>}</div><pre className="mt-3 whitespace-pre-wrap rounded-md bg-surface p-3 text-sm">{JSON.stringify(item.data, null, 2)}</pre><label className="mt-3 block text-sm font-semibold">Review remarks<textarea value={remarks[item.id] ?? ""} onChange={(event) => setRemarks((current) => ({ ...current, [item.id]: event.target.value }))} className="mt-1 min-h-20 w-full rounded-md border border-border p-3" /></label><div className="mt-3 flex gap-2"><button type="button" onClick={() => void decide(item, "ACCEPTED")} className="rounded-md bg-brand px-3 py-2 text-sm font-bold text-white">Accept</button><button type="button" onClick={() => void decide(item, "REJECTED")} className="rounded-md border border-red-300 px-3 py-2 text-sm font-bold text-red-800">Reject</button></div></article>)}</div>
    </section>
  );
}
