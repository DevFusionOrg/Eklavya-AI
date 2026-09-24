"use client";
/* eslint-disable @next/next/no-img-element */

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  claimApplication,
  getReviewPayload,
  submitOfficerAction,
  type OfficerAction,
  type ReviewPayload,
} from "../lib/api";

export default function ReviewWorkspace({ applicationId }: { applicationId: string }) {
  const [payload, setPayload] = useState<ReviewPayload | null>(null);
  const [documentIndex, setDocumentIndex] = useState(0);
  const [selectedField, setSelectedField] = useState<string>();
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [dialog, setDialog] = useState<OfficerAction["action"]>();
  const [reason, setReason] = useState("");
  const [remarks, setRemarks] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      setPayload(await getReviewPayload(applicationId));
    } catch {
      setNotice("Review payload could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [applicationId]);
  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName ?? "")) return;
      if (event.key === "j") setDocumentIndex((index) => Math.min((payload?.documents.length ?? 1) - 1, index + 1));
      if (event.key === "k") setDocumentIndex((index) => Math.max(0, index - 1));
      if (event.key === "v") setDialog("VERIFY");
      if (event.key === "d") setDialog("RAISE_DEFICIENCY");
      if (event.key === "r") setDialog("REJECT");
      if (event.key === "e") setDialog("ESCALATE");
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, [payload]);

  const selectedDocument = payload?.documents[documentIndex];
  const fieldsForDocument = useMemo(
    () => payload?.extracted_fields.filter((field) => field.document_id === selectedDocument?.id) ?? [],
    [selectedDocument?.id, payload?.extracted_fields],
  );

  async function claim() {
    try { await claimApplication(applicationId); setNotice("Application claimed."); await load(); }
    catch { setNotice("This application is already assigned to another officer."); }
  }

  async function submitAction() {
    if (!dialog) return;
    if (["RAISE_DEFICIENCY", "REJECT"].includes(dialog) && !reasonCode.trim()) {
      setNotice("A reason code is required for this action.");
      return;
    }
    if (dialog === "REJECT" && !remarks.trim()) {
      setNotice("Remarks are required when rejecting an application.");
      return;
    }
    setSubmitting(true);
    try {
      await submitOfficerAction(applicationId, { action: dialog, reason_code: reasonCode || undefined, remarks: remarks || reason || undefined, field: selectedField });
      setNotice(`${dialog.replace("_", " ")} recorded.`);
      setDialog(undefined);
      setReason("");
      setRemarks("");
      setReasonCode("");
      await load();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Action could not be recorded.");
    } finally { setSubmitting(false); }
  }

  if (loading) return <p className="rounded-xl bg-white p-6">Loading review workspace…</p>;
  if (!payload) return <p role="alert" className="rounded-xl bg-red-50 p-6 text-red-800">{notice}</p>;

  return (
    <section aria-labelledby="review-title">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div><Link href="/officer" className="text-sm font-semibold text-brand underline">← Queue</Link><h1 id="review-title" className="mt-2 text-2xl font-bold">Application review</h1><p className="text-xs text-muted">{applicationId} · {payload.application.status.replaceAll("_", " ")}</p></div>
        <button type="button" onClick={() => void claim()} className="rounded-md border border-border bg-white px-4 py-2 text-sm font-bold">Claim application</button>
      </div>
      {notice && <p role="status" className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-900">{notice}</p>}
      <div className="grid min-h-[620px] gap-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        <div className="rounded-xl border border-border bg-slate-900 p-3 text-white">
          <div className="mb-3 flex items-center justify-between gap-2"><h2 className="font-bold">Document evidence</h2><span className="text-xs text-slate-300">J/K documents · click evidence</span></div>
          <div className="mb-3 flex gap-2 overflow-x-auto">{payload.documents.map((item, index) => <button type="button" key={item.id} onClick={() => setDocumentIndex(index)} className={`whitespace-nowrap rounded-md px-3 py-2 text-xs font-bold ${index === documentIndex ? "bg-white text-slate-900" : "bg-slate-700 text-white"}`}>{item.doc_type}</button>)}</div>
          {selectedDocument ? <div className="relative min-h-[390px] overflow-hidden rounded-lg bg-slate-800">{selectedDocument.mime === "application/pdf" ? <iframe title={selectedDocument.doc_type} src={selectedDocument.signed_url} className="h-[520px] w-full bg-white" /> : /* eslint-disable-next-line @next/next/no-img-element */ <img src={selectedDocument.signed_url} alt={`${selectedDocument.doc_type} document`} className="mx-auto max-h-[520px] max-w-full object-contain" />}{fieldsForDocument.map((field) => <button type="button" key={field.field} title={`${field.field}: ${String(field.value)}`} onClick={() => setSelectedField(field.field)} className={`absolute h-8 w-24 border-2 ${selectedField === field.field ? "border-amber-300 bg-amber-300/30" : "border-cyan-300 bg-cyan-300/20"}`} style={bboxStyle(field.bbox)}>{field.field}</button>)}</div> : <p className="p-8 text-slate-300">No documents attached.</p>}
          <div className="mt-3 flex flex-wrap gap-2">{fieldsForDocument.map((field) => <button type="button" key={field.field} onClick={() => setSelectedField(field.field)} className="rounded-full bg-slate-700 px-3 py-1 text-xs">{field.field}: {Math.round(field.confidence * 100)}%</button>)}</div>
        </div>
        <div className="space-y-4 overflow-y-auto">
          <Panel title="Declared data">{Object.entries(payload.application.form_data).map(([key, value]) => <div className="flex justify-between gap-4 border-b border-border py-2 text-sm" key={key}><span className="font-semibold">{key}</span><span className="text-right text-muted">{String(value)}</span></div>)}</Panel>
          <Panel title="Extracted data">{payload.extracted_fields.map((field) => <button type="button" onClick={() => { setSelectedField(field.field); const index = payload.documents.findIndex((item) => item.id === field.document_id); if (index >= 0) setDocumentIndex(index); }} className={`flex w-full justify-between gap-3 border-b border-border py-2 text-left text-sm ${selectedField === field.field ? "bg-amber-50" : ""}`} key={`${field.document_id}-${field.field}`}><span className="font-semibold">{field.field}<span className="ml-2 text-xs text-brand underline">evidence</span></span><span>{String(field.value)} <Confidence value={field.confidence} /></span></button>)}</Panel>
          <Panel title="Rules"><div className="space-y-2">{payload.rules.map((rule, index) => <div className="rounded-md bg-surface p-2 text-sm" key={`${rule.rule_id}-${index}`}><span className={rule.passed === false || rule.pass === false ? "text-red-700" : "text-green-800"}>{rule.passed === false || rule.pass === false ? "FAIL" : "PASS"}</span> <span className="font-semibold">{rule.rule_id ?? `Rule ${index + 1}`}</span><p className="mt-1 text-xs text-muted">{rule.reason}</p></div>)}</div></Panel>
          <Panel title="AI recommendation">{payload.ai_recommendation ? <div className="text-sm"><p>{payload.ai_recommendation.summary}</p><p className="mt-2 font-bold">Suggested action: {payload.ai_recommendation.suggested_action ?? "Review evidence"}</p><p className="mt-1">Confidence <Confidence value={payload.ai_recommendation.confidence ?? 0} /></p>{payload.ai_recommendation.flagged_risks?.map((risk) => <p className="mt-2 text-amber-800" key={risk}>Risk: {risk}</p>)}</div> : <p className="text-sm text-muted">No AI recommendation. Use rules and source evidence.</p>}</Panel>
        </div>
      </div>
      <div className="sticky bottom-0 mt-4 flex flex-wrap gap-2 rounded-xl border border-border bg-white p-3 shadow-lg"><button type="button" onClick={() => setDialog("VERIFY")} className="rounded-md bg-brand px-4 py-3 font-bold text-white">Verify <kbd>V</kbd></button><button type="button" onClick={() => setDialog("RAISE_DEFICIENCY")} className="rounded-md border border-amber-400 px-4 py-3 font-bold text-amber-900">Raise deficiency <kbd>D</kbd></button><button type="button" onClick={() => setDialog("REJECT")} className="rounded-md border border-red-300 px-4 py-3 font-bold text-red-800">Reject <kbd>R</kbd></button><button type="button" onClick={() => setDialog("ESCALATE")} className="rounded-md border border-border px-4 py-3 font-bold">Escalate <kbd>E</kbd></button></div>
      {dialog && <ActionDialog action={dialog} reasonCode={reasonCode} remarks={remarks} setReasonCode={setReasonCode} setRemarks={setRemarks} onCancel={() => setDialog(undefined)} onSubmit={() => void submitAction()} submitting={submitting} />}
    </section>
  );
}

function bboxStyle(bbox: number[] | null): React.CSSProperties {
  if (!bbox || bbox.length < 4) return { left: "8%", top: "8%" };
  return { left: `${bbox[0]}%`, top: `${bbox[1]}%`, width: `${Math.max(8, bbox[2] - bbox[0])}%`, height: `${Math.max(5, bbox[3] - bbox[1])}%` };
}

function Confidence({ value }: { value: number }) {
  const percent = Math.round(value * 100);
  return <span className={`ml-2 rounded-full px-2 py-0.5 text-xs font-bold ${percent < 75 ? "bg-red-100 text-red-800" : percent < 90 ? "bg-amber-100 text-amber-800" : "bg-green-100 text-green-800"}`}>{percent}%</span>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-xl border border-border bg-white p-4"><h2 className="mb-3 font-bold">{title}</h2>{children}</section>;
}

function ActionDialog({ action, reasonCode, remarks, setReasonCode, setRemarks, onCancel, onSubmit, submitting }: { action: OfficerAction["action"]; reasonCode: string; remarks: string; setReasonCode: (value: string) => void; setRemarks: (value: string) => void; onCancel: () => void; onSubmit: () => void; submitting: boolean }) {
  const requiredReason = ["RAISE_DEFICIENCY", "REJECT"].includes(action);
  return <div className="fixed inset-0 z-20 flex items-end justify-center bg-slate-950/50 p-4 sm:items-center"><div role="dialog" aria-modal="true" aria-labelledby="action-title" className="w-full max-w-lg rounded-xl bg-white p-6"><h2 id="action-title" className="text-xl font-bold">{action.replace("_", " ")}</h2><p className="mt-1 text-sm text-muted">This action is audited and cannot be undone.</p>{requiredReason && <label className="mt-4 block text-sm font-semibold">Reason code<input required value={reasonCode} onChange={(event) => setReasonCode(event.target.value)} className="mt-1 w-full rounded-md border border-border px-3 py-3" placeholder="e.g. MISSING_DOCUMENT" /></label>}<label className="mt-4 block text-sm font-semibold">Remarks{action === "REJECT" && " (required)"}<textarea value={remarks} onChange={(event) => setRemarks(event.target.value)} className="mt-1 min-h-24 w-full rounded-md border border-border px-3 py-3" /></label><div className="mt-5 flex justify-end gap-2"><button type="button" onClick={onCancel} className="rounded-md border border-border px-4 py-2 font-semibold">Cancel</button><button type="button" disabled={submitting} onClick={onSubmit} className="rounded-md bg-brand px-4 py-2 font-bold text-white disabled:opacity-50">{submitting ? "Saving…" : "Confirm action"}</button></div></div></div>;
}
