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
      `${API_URL}/api/v1/applications/${applicationId}/documents?doc_type=${encodeURIComponent(docType)}`,
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
