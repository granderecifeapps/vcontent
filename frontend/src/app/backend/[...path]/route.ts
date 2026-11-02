import { NextRequest } from "next/server";

const TARGET = process.env.API_PROXY_TARGET || "http://127.0.0.1:8010";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const url = `${TARGET}/${path.join("/")}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);
  for (const name of ["host", "connection", "expect", "content-length", "transfer-encoding"]) {
    headers.delete(name);
  }
  const init: RequestInit & { duplex?: "half" } = {
    method: request.method,
    headers,
    redirect: "manual",
  };
  if (request.method !== "GET" && request.method !== "HEAD" && request.body) {
    init.body = request.body;
    init.duplex = "half";
  }
  const upstream = await fetch(url, init);
  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    const name = key.toLowerCase();
    if (name === "set-cookie" || name === "content-encoding" || name === "content-length") return;
    responseHeaders.append(key, value);
  });
  for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append("set-cookie", cookie);
  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
