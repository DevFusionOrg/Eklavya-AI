"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { landingForRole, saveAuth } from "../../lib/auth";
import { login } from "../../lib/api";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const auth = await login(String(data.get("email")), String(data.get("password")));
      const saved = saveAuth(auth);
      router.push(landingForRole(saved.user!.role));
    } catch {
      setError("We could not sign you in. Check your details and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main id="main-content" className="flex min-h-screen items-center justify-center px-4 py-10">
      <form className="w-full max-w-md rounded-xl border border-border bg-white p-6 shadow-sm sm:p-8" onSubmit={submit}>
        <p className="mb-2 text-sm font-semibold text-brand">Eklavya.AI</p>
        <h1 className="mb-2 text-2xl font-bold">Sign in</h1>
        <p className="mb-6 text-sm text-muted">Access your scholarship workspace securely.</p>
        {error && <p role="alert" className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        <label className="mb-4 block text-sm font-semibold" htmlFor="email">Email
          <input required id="email" name="email" type="email" autoComplete="email" className="mt-1 w-full rounded-md border border-border px-3 py-3" />
        </label>
        <label className="mb-6 block text-sm font-semibold" htmlFor="password">Password
          <input required id="password" name="password" type="password" autoComplete="current-password" className="mt-1 w-full rounded-md border border-border px-3 py-3" />
        </label>
        <button disabled={busy} className="w-full rounded-md bg-brand px-4 py-3 font-bold text-white hover:bg-green-800 disabled:opacity-60" type="submit">
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="mt-5 text-center text-sm text-muted">New applicant? <Link className="font-semibold text-brand underline" href="/register">Create an account</Link></p>
      </form>
    </main>
  );
}
