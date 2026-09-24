"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { landingForRole, saveAuth } from "../../lib/auth";
import { register } from "../../lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    try {
      const auth = await register(String(data.get("email")), String(data.get("password")));
      const saved = saveAuth(auth);
      router.push(landingForRole(saved.user!.role));
    } catch {
      setError("Registration failed. Use a valid email and a strong password.");
    }
  }
  return (
    <main id="main-content" className="flex min-h-screen items-center justify-center px-4 py-10">
      <form className="w-full max-w-md rounded-xl border border-border bg-white p-6 shadow-sm sm:p-8" onSubmit={submit}>
        <h1 className="mb-2 text-2xl font-bold">Create applicant account</h1>
        <p className="mb-6 text-sm text-muted">Officer accounts are created by an administrator.</p>
        {error && <p role="alert" className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        <label className="mb-4 block text-sm font-semibold" htmlFor="email">Email<input required id="email" name="email" type="email" className="mt-1 w-full rounded-md border border-border px-3 py-3" /></label>
        <label className="mb-6 block text-sm font-semibold" htmlFor="password">Password<input required minLength={12} id="password" name="password" type="password" className="mt-1 w-full rounded-md border border-border px-3 py-3" /></label>
        <button className="w-full rounded-md bg-brand px-4 py-3 font-bold text-white hover:bg-green-800" type="submit">Create account</button>
        <p className="mt-5 text-center text-sm text-muted"><Link className="font-semibold text-brand underline" href="/login">Back to sign in</Link></p>
      </form>
    </main>
  );
}
