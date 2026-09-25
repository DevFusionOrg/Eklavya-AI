"use client";

import { useEffect, useState } from "react";
import { listMyAwards, submitFollowup, uploadDocument, type AwardSummary } from "../lib/api";

function dueLabel(value: string | null) {
  if (!value) return "No due date";
  const days = Math.ceil((new Date(value).getTime() - Date.now()) / 86400000);
  return days < 0 ? `Overdue by ${Math.abs(days)} day${days === -1 ? "" : "s"}` : `${days} day${days === 1 ? "" : "s"} remaining`;
}

export default function FollowupPanel() {
  const [awards, setAwards] = useState<AwardSummary[]>([]);
  const [selected, setSelected] = useState<AwardSummary["requirements"][number]>();
  const [value, setValue] = useState("");
  const [notice, setNotice] = useState("");
  const [documentId, setDocumentId] = useState<string>();

  async function load() {
    try { setAwards(await listMyAwards()); }
    catch { setNotice("Award progress is temporarily unavailable."); }
  }
  useEffect(() => { void load(); }, []);

  async function submit() {
    if (!selected || !value.trim()) {
      setNotice("Add a response before submitting.");
      return;
    }
    try {
      await submitFollowup(selected.id, { response: value.trim() }, documentId);
      setNotice("Requirement submitted for officer review.");
      setSelected(undefined);
      setValue("");
      setDocumentId(undefined);
      await load();
    } catch { setNotice("Submission failed. Please try again."); }
  }

  if (!awards.length && !notice) return null;
  return (
    <section className="mt-6 rounded-xl border border-border bg-white p-5" aria-labelledby="followups-title">
      <h2 id="followups-title" className="text-lg font-bold">Award progress</h2>
      <p className="mt-1 text-sm text-muted">Submit each follow-up requirement before its due date to keep instalments on track.</p>
      {notice && <p role="status" className="mt-3 rounded-md bg-green-50 p-3 text-sm text-green-900">{notice}</p>}
      <div className="mt-4 space-y-4">
        {awards.map((award) => (
          <div className="rounded-lg border border-border p-4" key={award.id}>
            <div className="flex flex-wrap justify-between gap-2"><p className="font-bold">Award amount: ₹{award.amount}</p><span className="text-sm font-semibold text-brand">{award.status.replaceAll("_", " ")}</span></div>
            {award.instalments.length > 0 && <div className="mt-3 grid gap-2 sm:grid-cols-2">{award.instalments.map((instalment) => <div className="rounded-md bg-surface p-3 text-sm" key={instalment.label}><p className="font-semibold">{instalment.label}</p><p>₹{instalment.amount}</p>{instalment.due_date && <p className="text-xs text-muted">{new Date(instalment.due_date).toLocaleDateString()}</p>}</div>)}</div>}
            <h3 className="mt-4 text-sm font-bold">Upcoming requirements</h3>
            <div className="mt-2 space-y-2">{award.requirements.map((requirement) => <div className="flex flex-col gap-2 rounded-md border border-border p-3 sm:flex-row sm:items-center sm:justify-between" key={requirement.id}><div><p className="text-sm font-semibold">{requirement.name}</p><p className={`text-xs ${requirement.status === "OVERDUE" ? "text-red-700" : "text-muted"}`}>{requirement.status} · {dueLabel(requirement.due_date)}</p></div>{["UPCOMING", "OVERDUE", "REJECTED"].includes(requirement.status) && <button type="button" onClick={() => setSelected(requirement)} className="w-fit rounded-md bg-brand px-3 py-2 text-sm font-bold text-white">Submit</button>}</div>)}</div>
          </div>
        ))}
      </div>
      {selected && <div className="mt-4 rounded-lg border border-brand bg-green-50 p-4"><h3 className="font-bold">Submit: {selected.name}</h3><label className="mt-3 block text-sm font-semibold">Response<textarea autoFocus value={value} onChange={(event) => setValue(event.target.value)} className="mt-1 min-h-28 w-full rounded-md border border-border bg-white p-3" placeholder="Enter attendance, marks, utilisation details, or a note about your document." /></label><label className="mt-3 block text-sm font-semibold">Supporting document (optional)<input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" className="mt-1 block w-full text-sm" onChange={async (event) => { const file = event.target.files?.[0]; if (!file || !awards.length) return; try {       const result = await uploadDocument(awards[0].application_id, "followup", file, undefined, selected.id); setDocumentId(result.document_id); setNotice("Document uploaded and queued for OCR."); } catch { setNotice("Document upload failed."); } }} /></label><div className="mt-3 flex justify-end gap-2"><button type="button" onClick={() => setSelected(undefined)} className="rounded-md border border-border px-3 py-2 text-sm font-semibold">Cancel</button><button type="button" onClick={() => void submit()} className="rounded-md bg-brand px-3 py-2 text-sm font-bold text-white">Submit for review</button></div></div>}
    </section>
  );
}
