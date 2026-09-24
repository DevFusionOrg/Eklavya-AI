import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const role = request.cookies.get("eklavya_role")?.value;
  if (pathname.startsWith("/applicant") && role !== "APPLICANT") {
    return NextResponse.redirect(new URL(role ? "/officer" : "/login", request.url));
  }
  if (pathname.startsWith("/officer") && !role) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (pathname === "/login" && role) {
    return NextResponse.redirect(new URL(role === "APPLICANT" ? "/applicant" : "/officer", request.url));
  }
  return NextResponse.next();
}

export const config = { matcher: ["/login", "/applicant/:path*", "/officer/:path*"] };
