import { NextRequest, NextResponse } from "next/server";

function getApiBaseUrl(): string {
  return process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

type RouteContext = {
  params: Promise<{ docId: string }>;
};

export async function GET(_request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const { docId } = await context.params;

  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/documents/${encodeURIComponent(docId)}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        { detail: `Backend responded with status ${response.status}` },
        { status: response.status },
      );
    }

    const payload = await response.json();
    return NextResponse.json(payload);
  } catch {
    return NextResponse.json({ detail: "Backend is unreachable" }, { status: 503 });
  }
}
