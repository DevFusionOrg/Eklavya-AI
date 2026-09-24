import type { AuthResponse, Role } from "./api";

const AUTH_KEY = "eklavya.auth";

export function saveAuth(auth: AuthResponse): AuthResponse {
  const claims = JSON.parse(atob(auth.access_token.split(".")[1])) as {
    sub: string;
    role: Role;
  };
  const normalized = {
    ...auth,
    user: auth.user ?? { id: claims.sub, email: "", role: claims.role },
  };
  localStorage.setItem(AUTH_KEY, JSON.stringify(normalized));
  document.cookie = `eklavya_role=${normalized.user.role}; Path=/; SameSite=Lax`;
  return normalized;
}

export function readAuth(): AuthResponse | null {
  if (typeof window === "undefined") return null;
  const value = localStorage.getItem(AUTH_KEY);
  return value ? (JSON.parse(value) as AuthResponse) : null;
}

export function clearAuth() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_KEY);
  document.cookie = "eklavya_role=; Path=/; Max-Age=0; SameSite=Lax";
}

export function landingForRole(role: Role) {
  return role === "APPLICANT" ? "/applicant" : "/officer";
}
