"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  getApplicationDeficiencies,
  getApplicationTimeline,
  listMyApplications,
  listSchemes,
  type ApplicationSummary,
  type DeficiencyResponse,
  type Scheme,
  type TimelineEntry,
} from "../../lib/api";
import FollowupPanel from "../../components/followup-panel";

type ApplicationDetails = {
  timeline: TimelineEntry[];
  deficiencies: DeficiencyResponse;
};

function timeLeft(deadline: string | null) {
  if (!deadline) return null;
  const remaining = new Date(deadline).getTime() - Date.now();
  if (remaining <= 0) return "Deadline passed";
  const days = Math.floor(remaining / 86400000);
  const hours = Math.floor((remaining % 86400000) / 3600000);
  return `${days}d ${hours}h remaining`;
}

export default function ApplicantPage() {
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [details, setDetails] = useState<Record<string, ApplicationDetails>>({});
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [, setClock] = useState(Date.now());

  useEffect(() => {
    const interval = window.setInterval(() => setClock(Date.now()), 60000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    Promise.all([listMyApplications(), listSchemes()])
      .then(async ([items, availableSchemes]) => {
        setApplications(items);
        setSchemes(availableSchemes);
        const loaded = await Promise.all(
          items.map(async (item) => [
            item.id,
            {
              timeline: await getApplicationTimeline(item.id),
              deficiencies: await getApplicationDeficiencies(item.id),
            },
          ] as const),
        );
        setDetails(Object.fromEntries(loaded));
      })
      .catch(() => setNotice("We could not load your applications. Please try again."))
      .finally(() => setLoading(false));
  }, []);

  const counts = useMemo(
    () => ({
      drafts: applications.filter((item) => ["DRAFT", "DEFICIENT"].includes(item.status)).length,
      submitted: applications.filter((item) => !["DRAFT", "DEFICIENT", "CLOSED"].includes(item.status)).length,
      awards: applications.filter((item) => ["AWARDED", "APPROVED"].includes(item.status)).length,
    }),
    [applications],
  );

  return (
    <section aria-labelledby="applicant-title">
      <div className="mb-8">
        <p className="text-sm font-semibold text-brand">Applicant portal</p>
        <h1 id="applicant-title" className="mt-1 text-3xl font-bold">Your scholarship journey</h1>
        <p className="mt-2 max-w-2xl text-muted">Track progress, fix flagged items, and resubmit from your phone.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ["Drafts and corrections", counts.drafts],
          ["In review", counts.submitted],
          ["Awards", counts.awards],
        ].map(([label, count]) => (
          <div className="rounded-xl border border-border bg-white p-4" key={String(label)}>
            <p className="text-sm text-muted">{label}</p>
            <p className="mt-1 text-3xl font-bold">{count}</p>
          </div>
        ))}
      </div>
      {notice && <p role="alert" className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-800">{notice}</p>}
      {loading ? <p className="mt-6 rounded-xl bg-white p-6">Loading applications…</p> : (
        <div className="mt-6 space-y-4">
          {applications.map((application) => (
            <ApplicationCard key={application.id} application={application} details={details[application.id]} />
          ))}
          {!applications.length && <div className="rounded-xl border border-border bg-white p-6"><p className="font-semibold">No applications yet</p><p className="mt-1 text-sm text-muted">Choose an open scheme to get started.</p></div>}
        </div>
      )}
      <div className="mt-6 rounded-xl border border-border bg-white p-5">
        <h2 className="text-lg font-bold">Start an application</h2>
        <p className="mt-1 text-sm text-muted">Choose a scheme. The form and required documents load from its published configuration.</p>
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
      <FollowupPanel />
    </section>
  );
}

function ApplicationCard({ application, details }: { application: ApplicationSummary; details?: ApplicationDetails }) {
  const openDeficiencies = details?.deficiencies.items.filter((item) => item.status === "OPEN") ?? [];
  return (
    <article className="rounded-xl border border-border bg-white p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div><h2 className="text-lg font-bold">{application.scheme_name || "Scholarship application"}</h2><p className="mt-1 text-xs text-muted">Application {application.id.slice(0, 8).toUpperCase()}</p></div>
        <span className="w-fit rounded-full bg-green-50 px-3 py-1 text-sm font-bold text-brand">{application.status.replaceAll("_", " ")}</span>
      </div>
      {application.status === "DEFICIENT" && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div><h3 className="font-bold text-amber-950">Action needed</h3><p className="text-sm text-amber-900">{openDeficiencies.length} item{openDeficiencies.length === 1 ? "" : "s"} need correction.</p></div>
            <span className="text-sm font-bold text-amber-950">{timeLeft(application.correction_deadline)}</span>
          </div>
          <ul className="mt-3 space-y-2">{openDeficiencies.map((item) => <li className="flex items-start justify-between gap-3 text-sm" key={item.id}><span className="text-amber-950">{item.message}</span><Link className="shrink-0 font-bold text-brand underline" href={`/applicant/apply/${application.scheme_code}?application=${application.id}&field=${encodeURIComponent(item.field ?? "")}#corrections`}>Fix this</Link></li>)}</ul>
          <Link className="mt-4 inline-block rounded-md bg-brand px-4 py-2 text-sm font-bold text-white" href={`/applicant/apply/${application.scheme_code}?application=${application.id}#corrections`}>Review and resubmit</Link>
        </div>
      )}
      <div className="mt-5"><h3 className="text-sm font-bold">Status timeline</h3>{details ? <ol className="mt-3 space-y-3 border-l-2 border-green-100 pl-4">{details.timeline.map((entry, index) => <li key={`${entry.created_at}-${index}`} className="relative text-sm"><span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-brand" /><p className="font-semibold">{entry.to_status.replaceAll("_", " ")}</p><p className="text-xs text-muted">{new Date(entry.created_at).toLocaleString()} {entry.reason ? `· ${entry.reason}` : ""}</p></li>)}</ol> : <p className="mt-2 text-sm text-muted">Loading timeline…</p>}</div>
    </article>
  );
}
