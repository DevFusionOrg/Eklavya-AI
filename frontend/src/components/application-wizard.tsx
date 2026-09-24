"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  autosaveDraft,
  createDraft,
  getSchemeForm,
  getApplicationDeficiencies,
  listMyApplications,
  resubmitApplication,
  submitDraft,
  uploadDocument,
  type FormProperty,
  type SchemeForm,
} from "../lib/api";
import { displayLabel, schemaToZod, stepsFromSchema } from "../lib/schema-form";

type Props = { code: string };

export default function ApplicationWizard({ code }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const correctionId = searchParams.get("application");
  const focusedField = searchParams.get("field");
  const [form, setForm] = useState<SchemeForm | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [applicationId, setApplicationId] = useState<string>();
  const [stepIndex, setStepIndex] = useState(0);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState("");
  const [uploading, setUploading] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [loading, setLoading] = useState(true);
  const [review, setReview] = useState(false);
  const [editableFields, setEditableFields] = useState<Set<string> | null>(null);
  const [editableDocuments, setEditableDocuments] = useState<Set<string> | null>(null);

  useEffect(() => {
    getSchemeForm(code)
      .then(async (loadedForm) => {
        setForm(loadedForm);
        if (!correctionId) return;
        const [applications, deficiencyResponse] = await Promise.all([
          listMyApplications(),
          getApplicationDeficiencies(correctionId),
        ]);
        const application = applications.find((item) => item.id === correctionId);
        if (!application) throw new Error("Application not found");
        setApplicationId(application.id);
        setValues(application.form_data ?? {});
        const fields = new Set<string>();
        const documents = new Set<string>();
        deficiencyResponse.items
          .filter((item) => item.status === "OPEN")
          .forEach((item) => {
            if (item.field?.startsWith("document:")) documents.add(item.field.slice("document:".length));
            else if (item.field) fields.add(item.field);
          });
        setEditableFields(fields);
        setEditableDocuments(documents);
        setNotice("Only the fields and documents flagged by the officer can be changed.");
      })
      .catch(() => setNotice("This scheme is not available right now."))
      .finally(() => setLoading(false));
  }, [code, correctionId]);

  const steps = useMemo(() => (form ? stepsFromSchema(form) : []), [form]);
  const schema = useMemo(() => (form ? schemaToZod(form) : null), [form]);
  const currentStep = steps[stepIndex];

  useEffect(() => {
    if (!focusedField) return;
    const index = steps.findIndex((step) => step.fields.includes(focusedField));
    if (index >= 0) setStepIndex(index);
  }, [focusedField, steps]);

  function updateValue(name: string, value: unknown) {
    if (editableFields && !editableFields.has(name)) return;
    setValues((current) => ({ ...current, [name]: value }));
    setErrors((current) => {
      const next = { ...current };
      delete next[name];
      return next;
    });
  }

  function validateStep() {
    if (!schema || !currentStep) return true;
    const result = schema.safeParse(values);
    if (result.success) {
      setErrors({});
      return true;
    }
    const next: Record<string, string> = {};
    for (const issue of result.error.issues) {
      const field = String(issue.path[0]);
      if (currentStep.fields.includes(field)) next[field] = issue.message;
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function save() {
    if (!form) return;
    const payload = editableFields
      ? Object.fromEntries(Array.from(editableFields).map((field) => [field, values[field]]))
      : values;
    if (applicationId) await autosaveDraft(applicationId, payload);
    else {
      const draft = await createDraft(form.version_id, values);
      setApplicationId(draft.id);
    }
    setNotice("Saved just now");
  }

  async function next() {
    if (!validateStep()) return;
    try {
      await save();
      if (stepIndex < steps.length - 1) setStepIndex((index) => index + 1);
      else setReview(true);
    } catch {
      setNotice("We could not save your progress. Please try again.");
    }
  }

  async function submit() {
    if (!applicationId || !schema) return;
    const result = schema.safeParse(values);
    if (!result.success) {
      setNotice("Complete all required fields before submitting.");
      return;
    }
    try {
      const payload = editableFields
        ? Object.fromEntries(Array.from(editableFields).map((field) => [field, values[field]]))
        : values;
      await autosaveDraft(applicationId, payload);
      if (editableFields) await resubmitApplication(applicationId);
      else await submitDraft(applicationId);
      router.push("/applicant?submitted=1");
    } catch {
      setNotice("Submission failed. Please review the flagged items and try again.");
    }
  }

  async function handleUpload(docType: string, file: File) {
    if (!applicationId) {
      setNotice("Save the application before uploading documents.");
      return;
    }
    if (editableDocuments && !editableDocuments.has(docType)) {
      setNotice("This document is locked because it was not flagged for correction.");
      return;
    }
    setUploading(docType);
    setUploadProgress(0);
    try {
      const result = await uploadDocument(applicationId, docType, file, setUploadProgress);
      setNotice(
        result.quality?.messages?.join(" ") ||
          (result.accepted ? "Document uploaded and queued for review." : "Document needs attention."),
      );
    } catch {
      setNotice("Upload failed. Check the file type and try again.");
    } finally {
      setUploading(null);
      setUploadProgress(0);
    }
  }

  if (loading) return <p className="rounded-lg bg-white p-6">Loading scheme form…</p>;
  if (!form || !currentStep) return <p role="alert" className="rounded-lg bg-red-50 p-6 text-red-800">{notice}</p>;

  return (
    <section aria-labelledby="wizard-title">
      <Link className="text-sm font-semibold text-brand underline" href="/applicant">← Back to applications</Link>
      <div className="mb-6 mt-5">
        <p className="text-sm font-semibold text-brand">{form.scheme.name}</p>
        <h1 id="wizard-title" className="mt-1 text-3xl font-bold">{review ? "Review and submit" : "Application form"}</h1>
        <p className="mt-2 text-sm text-muted">Scheme version {form.version_number}. {editableFields ? "Only flagged items are unlocked for correction." : "Your progress saves as you move between steps."}</p>
      </div>
      {notice && <p role="status" className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-900">{notice}</p>}
      {!review && (
        <ol aria-label="Application steps" className="mb-6 flex gap-2 overflow-x-auto">
          {steps.map((step, index) => <li key={step.id}><button type="button" onClick={() => index <= stepIndex && setStepIndex(index)} className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold ${index === stepIndex ? "bg-brand text-white" : index < stepIndex ? "bg-green-100 text-brand" : "bg-white text-muted"}`} aria-current={index === stepIndex ? "step" : undefined}>{index + 1}. {step.label}</button></li>)}
        </ol>
      )}
      {review ? (
        <Review values={values} form={form} onEdit={() => setReview(false)} onSubmit={submit} />
      ) : (
        <div className="rounded-xl border border-border bg-white p-5 sm:p-8">
          <div className="grid gap-5 md:grid-cols-2">
            {currentStep.fields.map((name) => <DynamicField key={name} name={name} property={form.form_schema.properties?.[name]} value={values[name]} error={errors[name]} locked={Boolean(editableFields && !editableFields.has(name))} onChange={updateValue} />)}
          </div>
          {stepIndex === steps.length - 1 && <DocumentSection documents={form.documents} uploading={uploading} uploadProgress={uploadProgress} editableDocuments={editableDocuments} onUpload={handleUpload} />}
          <div className="mt-8 flex justify-between gap-3">
            <button type="button" disabled={stepIndex === 0} onClick={() => setStepIndex((index) => Math.max(0, index - 1))} className="rounded-md border border-border px-4 py-3 font-semibold disabled:opacity-40">Back</button>
            <button type="button" onClick={next} className="rounded-md bg-brand px-5 py-3 font-bold text-white hover:bg-green-800">{stepIndex === steps.length - 1 ? "Review application" : "Save and continue"}</button>
          </div>
        </div>
      )}
    </section>
  );
}

function DynamicField({ name, property, value, error, locked, onChange }: { name: string; property?: FormProperty; value: unknown; error?: string; locked: boolean; onChange: (name: string, value: unknown) => void }) {
  if (!property) return null;
  const id = `field-${name}`;
  const inputType = property.type === "number" || property.type === "integer" ? "number" : property.format === "date" ? "date" : "text";
  return (
    <label className="block text-sm font-semibold" htmlFor={id}>
      {displayLabel(name, property)}
      {property.description && <span className="mt-1 block text-xs font-normal text-muted">{property.description}</span>}
      {property.enum ? <select id={id} value={String(value ?? "")} onChange={(event) => onChange(name, event.target.value)} className="mt-2 w-full rounded-md border border-border px-3 py-3"><option value="">Select an option</option>{property.enum.map((option) => <option key={option} value={option}>{option}</option>)}</select> :
        property.type === "boolean" ? <input id={id} type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(name, event.target.checked)} className="ml-3 h-5 w-5 align-middle" /> :
          <input id={id} disabled={locked} type={inputType} value={String(value ?? "")} onChange={(event) => onChange(name, inputType === "number" ? Number(event.target.value) : event.target.value)} className={`mt-2 w-full rounded-md border px-3 py-3 ${error ? "border-red-500" : "border-border"} ${locked ? "bg-slate-100 text-muted" : ""}`} />}
      {locked && <span className="mt-1 block text-xs font-normal text-muted">Locked — only officer-flagged fields can be changed.</span>}
      {error && <span role="alert" className="mt-1 block text-xs font-normal text-red-700">{error}</span>}
    </label>
  );
}

function DocumentSection({ documents, uploading, uploadProgress, editableDocuments, onUpload }: { documents: SchemeForm["documents"]; uploading: string | null; uploadProgress: number; editableDocuments: Set<string> | null; onUpload: (type: string, file: File) => void }) {
  return <div id="corrections" className="mt-8 border-t border-border pt-6"><h2 className="text-lg font-bold">Documents</h2><p className="mt-1 text-sm text-muted">Upload PDF, JPG, or PNG files. Image quality is checked instantly.</p><div className="mt-4 grid gap-4 md:grid-cols-2">{documents.map((document) => { const locked = Boolean(editableDocuments && !editableDocuments.has(document.doc_type)); return <label className={`rounded-lg border border-dashed border-border p-4 text-sm ${locked ? "bg-slate-50" : ""}`} key={document.doc_type}><span className="font-semibold">{document.label}</span>{document.mandatory && <span className="ml-2 text-red-700" aria-label="required">*</span>}{locked && <span className="mt-1 block text-xs text-muted">Locked — not flagged for correction.</span>}<input className="mt-3 block w-full text-sm" type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" disabled={locked || uploading === document.doc_type} onChange={(event) => { const file = event.target.files?.[0]; if (file) void onUpload(document.doc_type, file); }} />{uploading === document.doc_type && <><progress className="mt-3 h-2 w-full" max="100" value={uploadProgress}>{uploadProgress}%</progress><span className="mt-1 block text-xs text-brand" role="status">Uploading {uploadProgress}%</span></>}</label>; })}</div></div>;
}

function Review({ values, form, onEdit, onSubmit }: { values: Record<string, unknown>; form: SchemeForm; onEdit: () => void; onSubmit: () => void }) {
  return <div className="rounded-xl border border-border bg-white p-5 sm:p-8"><h2 className="text-xl font-bold">Check your details</h2><p className="mt-2 text-sm text-muted">Confirm every answer before submitting. You can return to edit any step.</p><dl className="mt-6 divide-y divide-border">{Object.entries(form.form_schema.properties ?? {}).map(([name, property]) => <div className="grid gap-1 py-3 sm:grid-cols-3" key={name}><dt className="text-sm font-semibold">{displayLabel(name, property)}</dt><dd className="sm:col-span-2 text-sm text-muted">{String(values[name] ?? "Not provided")}</dd></div>)}</dl><div className="mt-8 flex flex-wrap justify-end gap-3"><button type="button" onClick={onEdit} className="rounded-md border border-border px-4 py-3 font-semibold">Edit answers</button><button type="button" onClick={onSubmit} className="rounded-md bg-brand px-5 py-3 font-bold text-white hover:bg-green-800">Submit application</button></div></div>;
}
