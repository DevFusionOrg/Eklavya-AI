"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearAuth, readAuth } from "../lib/auth";

export function Shell({
  kind,
  children,
}: {
  kind: "applicant" | "officer" | "admin";
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const auth = readAuth();
  const links =
    kind === "applicant"
      ? [{ href: "/applicant", label: "My applications" }]
      : kind === "admin"
        ? [{ href: "/admin", label: "Administration" }]
      : [
          { href: "/officer", label: "Scrutiny queue" },
          { href: "/officer/review", label: "Verification" },
          { href: "/officer/analytics", label: "Analytics" },
        ];

  function signOut() {
    clearAuth();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-surface">
      <header className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link className="text-lg font-bold text-brand" href={`/${kind}`}>
            Eklavya<span className="text-ink">.AI</span>
          </Link>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted sm:inline">{auth?.user?.email}</span>
            <button className="rounded-md border border-border px-3 py-2 text-sm font-semibold hover:bg-surface" onClick={signOut}>
              Sign out
            </button>
          </div>
        </div>
      </header>
      <div className="mx-auto flex max-w-7xl flex-col md:flex-row">
        <aside className="border-b border-border bg-white md:min-h-[calc(100vh-73px)] md:w-60 md:border-b-0 md:border-r">
          <nav aria-label={`${kind} navigation`} className="flex gap-2 overflow-x-auto p-4 md:flex-col">
            {links.map((link) => (
              <Link
                className={`whitespace-nowrap rounded-md px-3 py-2 text-sm font-semibold ${
                  pathname === link.href ? "bg-green-50 text-brand" : "text-muted hover:bg-surface"
                }`}
                href={link.href}
                key={link.href}
                aria-current={pathname === link.href ? "page" : undefined}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </aside>
        <main id="main-content" className="min-w-0 flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
