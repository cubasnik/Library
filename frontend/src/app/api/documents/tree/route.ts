import { NextResponse } from "next/server";

function getApiBaseUrl(): string {
  return process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export async function GET(): Promise<NextResponse> {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/documents/tree`, {
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
