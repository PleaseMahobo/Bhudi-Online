import { verifyAccessToken } from "@/lib/jwt";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function GET() {
  const cookieStore = await cookies();

  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    return NextResponse.json(
      {
        authenticated: false,
      },
      { status: 401 }
    );
  }

  try {
    const payload = await verifyAccessToken(token);

    return NextResponse.json({
      authenticated: true,
      user: payload,
    });
  } catch {
    return NextResponse.json(
      {
        authenticated: false,
      },
      { status: 401 }
    );
  }
}