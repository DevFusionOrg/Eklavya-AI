"use client";

import { useEffect, useState } from "react";
import { Shell } from "../../components/shell";
import {
  createOfficer, createScheme, createSchemeVersion, dryRunRules, listAuditHistory,
  listOfficers, listSchemeVersions, listSchemes, publishSchemeVersion, verifyAuditChain,
  type AdminOfficer, type AuditEntry, type Scheme, type SchemeVersion,
} from "../../lib/api";

const blankJson = JSON.stringify({ type: "object", properties: {}, required: [] }, null, 2);

export default function AdminPage() {
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [selected, setSelected] = useState<Scheme | null>(null);
  const [versions, setVersions] = useState<SchemeVersion[]>([]);
  const [officers, setOfficers] = useState<AdminOfficer[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [form, setForm] = useState(blankJson);
  const [rules, setRules] = useState("{}");
  const [context, setContext] = useState("{}");
  const [message, setMessage] = useState("");
  const [newOfficer, setNewOfficer] = useState({ email: "", password: "", role: "SCRUTINY_OFFICER" as const });
  const [schemeDraft, setSchemeDraft] = useState({ code: "", name: "", description: "" });

  async function refresh() {
    const [s, o, a] = await Promise.all([listSchemes(), listOfficers(), listAuditHistory()]);
    setSchemes(s); setOfficers(o); setAudit(a);
    if (selected) setVersions(await listSchemeVersions(selected.id));
  }
  useEffect(() => { void refresh(); }, []);
  async function choose(scheme: Scheme) {
    setSelected(scheme); setVersions(await listSchemeVersions(scheme.id));
  }
  async function saveVersion() {
    if (!selected) return;
    try {
      const parsed = JSON.parse(form) as Record<string, unknown>;
      const version = await createSchemeVersion(selected.id, {
        form_schema: parsed, ui_hints: {}, eligibility_rules: JSON.parse(rules),
        selection_rules: {}, rules: {}, documents: [],
      });
      setMessage(`Draft version ${version.version_number} created.`);
      await choose(selected);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Invalid JSON or request failed"); }
  }
  async function runRules() {
    if (!selected) return;
    try {
      const result = await dryRunRules(selected.id, { rules: JSON.parse(rules), context: JSON.parse(context) });
      setMessage(JSON.stringify(result, null, 2));
    } catch (error) { setMessage(error instanceof Error ? error.message : "Dry-run failed"); }
  }
  return (
    <Shell kind="admin">
      <div className="space-y-8">
        <div><h1 className="text-2xl font-bold">Administration</h1><p className="text-muted">Manage versioned schemes, officers, and audit integrity.</p></div>
        {message && <pre className="whitespace-pre-wrap rounded-md bg-slate-100 p-3 text-sm">{message}</pre>}
        <section className="grid gap-4 lg:grid-cols-[18rem_1fr]">
          <div className="rounded-lg border border-border bg-white p-4">
            <h2 className="mb-3 font-semibold">Schemes</h2>
            <div className="space-y-2">{schemes.map((s) => <button className={`block w-full rounded p-2 text-left ${selected?.id === s.id ? "bg-green-50" : "hover:bg-surface"}`} key={s.id} onClick={() => void choose(s)}>{s.code} · {s.name}</button>)}</div>
            <div className="mt-5 space-y-2 border-t pt-4">
              <input className="input" placeholder="CODE" value={schemeDraft.code} onChange={(e) => setSchemeDraft({ ...schemeDraft, code: e.target.value })} />
              <input className="input" placeholder="Scheme name" value={schemeDraft.name} onChange={(e) => setSchemeDraft({ ...schemeDraft, name: e.target.value })} />
              <button className="button-primary w-full" onClick={async () => { await createScheme(schemeDraft); setSchemeDraft({ code: "", name: "", description: "" }); await refresh(); }}>Create scheme</button>
            </div>
          </div>
          <div className="space-y-4 rounded-lg border border-border bg-white p-4">
            <h2 className="font-semibold">{selected ? `${selected.name}: version builder` : "Select a scheme"}</h2>
            {selected && <><textarea className="min-h-56 w-full rounded border p-3 font-mono text-sm" value={form} onChange={(e) => setForm(e.target.value)} aria-label="Form JSON schema" /><div className="grid gap-3 md:grid-cols-2"><textarea className="min-h-32 rounded border p-3 font-mono text-sm" value={rules} onChange={(e) => setRules(e.target.value)} aria-label="Eligibility rules JSON" /><textarea className="min-h-32 rounded border p-3 font-mono text-sm" value={context} onChange={(e) => setContext(e.target.value)} aria-label="Dry run context JSON" /></div><div className="flex gap-2"><button className="button-primary" onClick={() => void saveVersion()}>Save draft version</button><button className="button-secondary" onClick={() => void runRules()}>Run eligibility dry-run</button></div>
              <div><h3 className="mb-2 font-semibold">Version history</h3>{versions.map((v) => <div className="flex items-center justify-between border-b py-2 text-sm" key={v.id}><span>v{v.version_number} · {v.status}</span>{v.status === "DRAFT" && <button className="button-secondary" onClick={async () => { await publishSchemeVersion(selected.id, v.id); await choose(selected); }}>Publish</button>}</div>)}</div></>}
          </div>
        </section>
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-border bg-white p-4"><h2 className="mb-3 font-semibold">Officer accounts</h2><div className="mb-4 grid gap-2 md:grid-cols-3"><input className="input" placeholder="Email" value={newOfficer.email} onChange={(e) => setNewOfficer({ ...newOfficer, email: e.target.value })} /><input className="input" placeholder="Password" type="password" value={newOfficer.password} onChange={(e) => setNewOfficer({ ...newOfficer, password: e.target.value })} /><button className="button-primary" onClick={async () => { await createOfficer(newOfficer.email, newOfficer.password, newOfficer.role); await refresh(); }}>Add officer</button></div>{officers.map((o) => <div className="border-b py-2 text-sm" key={o.id}>{o.email} · {o.role} · {o.is_active ? "Active" : "Inactive"}</div>)}</div>
          <div className="rounded-lg border border-border bg-white p-4"><div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">Audit log</h2><button className="button-secondary" onClick={async () => setMessage(JSON.stringify(await verifyAuditChain(), null, 2))}>Verify chain</button></div><div className="max-h-64 overflow-auto text-sm">{audit.map((a) => <div className="border-b py-2" key={a.id}>{a.action} · {a.entity_type} · {new Date(a.created_at).toLocaleString()}</div>)}</div></div>
        </section>
      </div>
    </Shell>
  );
}
