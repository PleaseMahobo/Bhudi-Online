import { NextResponse } from "next/server";

export async function POST() {
  return NextResponse.json(
    {
      success: false,
      message: "Refresh token flow not implemented yet",
    },
    { status: 501 }
  );
}