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

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!response.ok) {
    throw new Error((await response.text()) || "Request failed");
  }
  return response.json() as Promise<T>;
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
