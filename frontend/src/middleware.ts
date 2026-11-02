import { NextResponse, type NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const role = request.cookies.get("vc_role")?.value;
  const session = request.cookies.get("vc_access")?.value || request.cookies.get("vc_refresh")?.value;
  if ((pathname.startsWith("/admin") || pathname.startsWith("/portal")) && !session) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  if (pathname.startsWith("/admin") && role === "client") return NextResponse.redirect(new URL("/portal", request.url));
  if (pathname.startsWith("/portal") && role === "admin") return NextResponse.redirect(new URL("/admin", request.url));
  if (pathname === "/login" && session && role) {
    return NextResponse.redirect(new URL(role === "admin" ? "/admin" : "/portal", request.url));
  }
  return NextResponse.next();
}

export const config = { matcher: ["/admin/:path*", "/portal/:path*", "/login"] };
