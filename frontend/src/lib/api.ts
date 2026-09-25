export type Role =
  | "APPLICANT"
  | "SCRUTINY_OFFICER"
  | "VERIFYING_OFFICER"
  | "COMMITTEE_MEMBER"
  | "ADMIN";

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user?: { id: string; email: string; role: Role };
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function accessToken() {
  if (typeof window === "undefined") return undefined;
  return (JSON.parse(localStorage.getItem("eklavya.auth") ?? "null")?.access_token as
    | string
    | undefined);
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = accessToken();
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    throw new Error((await response.text()) || "Request failed");
  }
  return response.json() as Promise<T>;
}

export type Scheme = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
};

export type FormProperty = {
  type: "string" | "number" | "integer" | "boolean" | "array" | "object";
  title?: string;
  description?: string;
  enum?: string[];
  format?: string;
  minLength?: number;
  maxLength?: number;
  minimum?: number;
  maximum?: number;
  ["ui:step"]?: string;
  ["ui:widget"]?: string;
};

export type SchemeForm = {
  scheme: { code: string; name: string };
  version_id: string;
  version_number: number;
  form_schema: {
    type?: string;
    required?: string[];
    properties?: Record<string, FormProperty>;
  };
  ui_hints: Record<string, unknown>;
  documents: Array<{
    doc_type: string;
    label: string;
    mandatory: boolean;
    validity_rules: Record<string, unknown>;
  }>;
};

export type ApplicationDraft = {
  id: string;
  status: string;
  scheme_version_id: string;
  form_data?: Record<string, unknown>;
};

export type ApplicationSummary = ApplicationDraft & {
  scheme_code: string;
  scheme_name: string;
  correction_round: number;
  correction_deadline: string | null;
};

export type TimelineEntry = {
  from_status: string | null;
  to_status: string;
  reason: string | null;
  created_at: string;
};

export type Deficiency = {
  id: string;
  code: string;
  message: string;
  field: string | null;
  document_id: string | null;
  severity: string;
  status: string;
};

export type DeficiencyResponse = {
  repeat_deficiency_cycles: number;
  correction_round: number;
  correction_deadline: string | null;
  items: Deficiency[];
};

export type QueueItem = {
  id: string;
  scheme: string;
  status: string;
  scrutiny_officer_id: string | null;
  verifying_officer_id: string | null;
};

export type ReviewDocument = {
  id: string;
  doc_type: string;
  mime: string;
  ocr_status: string;
  signed_url: string;
  expires_in: number;
};

export type ExtractedField = {
  field: string;
  value: unknown;
  confidence: number;
  bbox: number[] | null;
  document_id: string;
};

export type RuleResult = {
  rule_id?: string;
  passed?: boolean;
  pass?: boolean;
  reason?: string;
  inputs?: Record<string, unknown>;
};

export type ReviewPayload = {
  application: {
    id: string;
    status: string;
    form_data: Record<string, unknown>;
  };
  documents: ReviewDocument[];
  extracted_fields: ExtractedField[];
  rules: RuleResult[];
  ai_recommendation: {
    summary?: string;
    suggested_action?: string;
    confidence?: number;
    flagged_risks?: string[];
    criteria?: Array<{ criterion?: string; assessment?: string; passed?: boolean }>;
    evidence?: Array<{ field?: string; document_id?: string; bbox?: number[]; quote?: string }>;
  } | null;
};

export async function getOfficerQueue(params: {
  scheme?: string;
  status?: string;
  deficiency_severity?: string;
  confidence_band?: string;
  sort?: string;
}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  return apiRequest<{ items: QueueItem[]; page: number; page_size: number; total: number }>(
    `/api/v1/officer/queue?${query.toString()}`,
  );
}

export async function claimApplication(applicationId: string) {
  return apiRequest<{ id: string; claimed_by: string; role: string }>(
    `/api/v1/officer/applications/${applicationId}/claim`,
    { method: "POST" },
  );
}

export async function getReviewPayload(applicationId: string) {
  return apiRequest<ReviewPayload>(
    `/api/v1/officer/applications/${applicationId}/review`,
  );
}

export type OfficerAction = {
  action: "VERIFY" | "RAISE_DEFICIENCY" | "REJECT" | "ESCALATE";
  reason_code?: string;
  remarks?: string;
  field?: string;
  document_id?: string;
  severity?: string;
  override_source?: "NONE" | "AI" | "RULES";
};

export async function submitOfficerAction(
  applicationId: string,
  action: OfficerAction,
) {
  return apiRequest<{ id: string; status: string; action: string }>(
    `/api/v1/officer/applications/${applicationId}/actions`,
    { method: "POST", body: JSON.stringify(action) },
  );
}

export type AwardSummary = {
  id: string;
  application_id: string;
  amount: string;
  instalments: Array<{ label: string; amount: string; due_date: string | null }>;
  status: string;
  requirements: Array<{
    id: string;
    name: string;
    type: string;
    due_date: string | null;
    status: string;
  }>;
};

export async function listMyAwards() {
  return apiRequest<AwardSummary[]>("/api/v1/followups/mine");
}

export async function submitFollowup(
  requirementId: string,
  data: Record<string, unknown>,
  documentId?: string,
) {
  return apiRequest<{ id: string; requirement_id: string; status: string }>(
    `/api/v1/followups/${requirementId}/submissions`,
    {
      method: "POST",
      body: JSON.stringify({ data, document_id: documentId || null }),
    },
  );
}

export type FollowupReviewItem = {
  id: string;
  requirement_id: string;
  requirement: string;
  application_id: string;
  award_id: string;
  data: Record<string, unknown>;
  document_id: string | null;
};

export async function listFollowupReviews() {
  return apiRequest<FollowupReviewItem[]>("/api/v1/followups/review");
}

export async function reviewFollowup(
  submissionId: string,
  status: "ACCEPTED" | "REJECTED",
  remarks: string,
) {
  return apiRequest<{ id: string; status: string }>(
    `/api/v1/followups/submissions/${submissionId}/review`,
    { method: "POST", body: JSON.stringify({ status, remarks }) },
  );
}

export async function listMyApplications() {
  return apiRequest<ApplicationSummary[]>("/api/v1/applications");
}

export async function getApplicationTimeline(applicationId: string) {
  return apiRequest<TimelineEntry[]>(
    `/api/v1/applications/${applicationId}/timeline`,
  );
}

export async function getApplicationDeficiencies(applicationId: string) {
  return apiRequest<DeficiencyResponse>(
    `/api/v1/applications/${applicationId}/deficiencies`,
  );
}

export async function resubmitApplication(applicationId: string) {
  return apiRequest<{ id: string; status: string; correction_round: number }>(
    `/api/v1/applications/${applicationId}/resubmit`,
    { method: "POST" },
  );
}

export async function listSchemes() {
  return apiRequest<Scheme[]>("/api/v1/schemes");
}

export async function getSchemeForm(code: string) {
  return apiRequest<SchemeForm>(
    `/api/v1/schemes/${encodeURIComponent(code)}/form-schema`,
  );
}

export async function createDraft(
  schemeVersionId: string,
  formData: Record<string, unknown>,
) {
  return apiRequest<ApplicationDraft>("/api/v1/applications", {
    method: "POST",
    body: JSON.stringify({
      scheme_version_id: schemeVersionId,
      form_data: formData,
    }),
  });
}

export async function autosaveDraft(
  applicationId: string,
  formData: Record<string, unknown>,
) {
  return apiRequest<ApplicationDraft>(
    `/api/v1/applications/${applicationId}`,
    { method: "PATCH", body: JSON.stringify({ form_data: formData }) },
  );
}

export async function submitDraft(applicationId: string) {
  return apiRequest<ApplicationDraft>(
    `/api/v1/applications/${applicationId}/submit`,
    { method: "POST" },
  );
}

export async function uploadDocument(
  applicationId: string,
  docType: string,
  file: File,
  onProgress?: (percent: number) => void,
  followupRequirementId?: string,
) {
  const body = new FormData();
  body.append("file", file);
  const token = accessToken();
  return new Promise<{
    accepted: boolean;
    quality?: { messages?: string[] };
    document_id?: string;
  }>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open(
      "POST",
      `${API_URL}/api/v1/applications/${applicationId}/documents?doc_type=${encodeURIComponent(docType)}${followupRequirementId ? `&followup_requirement_id=${encodeURIComponent(followupRequirementId)}` : ""}`,
    );
    if (token) request.setRequestHeader("Authorization", `Bearer ${token}`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        resolve(JSON.parse(request.responseText) as {
          accepted: boolean;
          quality?: { messages?: string[] };
          document_id?: string;
        });
      } else reject(new Error(request.responseText || "Upload failed"));
    };
    request.onerror = () => reject(new Error("Upload failed"));
    request.send(body);
  });
}

export async function login(email: string, password: string) {
  return apiRequest<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(email: string, password: string) {
  return apiRequest<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}
