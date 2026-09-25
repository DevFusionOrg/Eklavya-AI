"use client";

import { useEffect, useState } from "react";
import {
  downloadAnalytics,
  getAnalyticsSummary,
  type AnalyticsSummary,
} from "../../../lib/api";

function Percent({ value }: { value: number }) {
  return <span>{(value * 100).toFixed(1)}%</span>;
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary>();
  const [notice, setNotice] = useState("");

  useEffect(() => {
    getAnalyticsSummary().then(setSummary).catch(() => setNotice("Analytics are unavailable right now."));
  }, []);

  if (!summary) return <p className="rounded-xl bg-white p-6">{notice || "Loading analytics…"}</p>;
  return (
    <section aria-labelledby="analytics-title">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div><p className="text-sm font-semibold text-brand">Officer portal</p><h1 id="analytics-title" className="mt-1 text-3xl font-bold">Dashboards and reports</h1><p className="mt-2 text-sm text-muted">Generated {new Date(summary.generated_at).toLocaleString()} from persisted application records.</p></div>
        <div className="flex gap-2"><button type="button" onClick={() => void downloadAnalytics("csv")} className="rounded-md border border-border bg-white px-3 py-2 text-sm font-bold">CSV</button><button type="button" onClick={() => void downloadAnalytics("pdf")} className="rounded-md bg-brand px-3 py-2 text-sm font-bold text-white">PDF</button></div>
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-4">{Object.entries(summary.totals).map(([key, value]) => <div className="rounded-xl border border-border bg-white p-4" key={key}><p className="text-xs uppercase tracking-wide text-muted">{key.replaceAll("_", " ")}</p><p className="mt-2 text-3xl font-bold">{value}</p></div>)}</div>
      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Panel title="Application funnel"><div className="space-y-3">{summary.funnel.map((item) => <div key={item.stage}><div className="flex justify-between text-sm"><span>{item.stage.replaceAll("_", " ")}</span><b>{item.count}</b></div><div className="mt-1 h-2 rounded bg-surface"><div className="h-2 rounded bg-brand" style={{ width: `${summary.funnel[0].count ? Math.max(2, (item.count / summary.funnel[0].count) * 100) : 0}%` }} /></div></div>)}</div></Panel>
        <Panel title="Time per stage (days)"><MetricList items={Object.entries(summary.average_time_per_stage_days).map(([label, value]) => ({ label, value: `${value} days` }))} /></Panel>
        <Panel title="Deficiency causes"><MetricList items={summary.deficiency_causes.map((item) => ({ label: item.code, value: item.count }))} /></Panel>
        <Panel title="Quality and oversight"><div className="grid gap-3 sm:grid-cols-2"><Metric label="Repeat deficiency rate" value={<Percent value={summary.repeat_deficiency_rate.rate} />} /><Metric label="Override rate" value={<Percent value={summary.override_rate.rate} />} /><Metric label="AI overrides" value={summary.override_rate.by_source.AI ?? 0} /><Metric label="Rules overrides" value={summary.override_rate.by_source.RULES ?? 0} /></div><h3 className="mt-5 text-sm font-bold">OCR confidence</h3><MetricList items={Object.entries(summary.ocr_confidence).map(([label, value]) => ({ label, value }))} /></Panel>
        <Panel title="Scheme performance"><div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">Application counts by scheme and status</caption><thead><tr className="border-b border-border text-xs uppercase text-muted"><th className="py-2">Scheme</th><th className="py-2">Statuses</th></tr></thead><tbody>{summary.scheme_performance.map((item) => <tr className="border-b border-border" key={item.scheme}><td className="py-3 font-semibold">{item.scheme}</td><td className="py-3 text-muted">{Object.entries(item.statuses).map(([status, count]) => `${status}: ${count}`).join(" · ")}</td></tr>)}</tbody></table></div></Panel>
        <Panel title="State-wise distribution"><MetricList items={summary.state_distribution.map((item) => ({ label: item.state, value: item.count }))} /></Panel>
      </div>
      <p className="mt-6 text-xs text-muted">Definitions: {Object.values(summary.definitions).join(" ")}</p>
    </section>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-xl border border-border bg-white p-5"><h2 className="mb-4 text-lg font-bold">{title}</h2>{children}</section>;
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="rounded-lg bg-surface p-3"><p className="text-xs text-muted">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></div>;
}

function MetricList({ items }: { items: Array<{ label: string; value: string | number }> }) {
  return <div className="space-y-2">{items.length ? items.map((item) => <div className="flex justify-between gap-4 border-b border-border py-2 text-sm" key={item.label}><span>{item.label.replaceAll("_", " ")}</span><b>{item.value}</b></div>) : <p className="text-sm text-muted">No data yet.</p>}</div>;
}
