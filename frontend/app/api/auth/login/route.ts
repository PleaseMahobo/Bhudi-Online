import { NextResponse } from "next/server";
import { LoginSchema } from "@/lib/auth";
import { signAccessToken } from "@/lib/jwt";
import { randomBytes } from "crypto";
import { verifyPassword } from "@/lib/password";
import { prisma } from "@/lib/prisma";

// Authenticate user from the database.
export async function POST(request: Request) {
  try {
    const body = await request.json();

    const parsed = LoginSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        {
          success: false,
          message: "Invalid request",
          errors: parsed.error.flatten(),
        },
        { status: 400 }
      );
    }

    const user = await prisma.user.findUnique({
      where: {
        email: parsed.data.email,
      },
    });

    if (!user) {
      return NextResponse.json(
        {
          success: false,
          message: "Invalid email or password",
        },
        { status: 401 }
      );
    }

    const validPassword = await verifyPassword(
      parsed.data.password,
      user.passwordHash
     );
    

    if (!validPassword) {
      return NextResponse.json(
        {
          success: false,
          message: "Invalid email or password",
        },
        { status: 401 }
      );
    }

    // create tokens
    const token = await signAccessToken({ sub: user.id, email: user.email, role: user.role });
    const refreshToken = randomBytes(40).toString("hex");
    const expiryDate = new Date(Date.now() + 1000 * 60 * 60 * 24 * 30); // 30 days

    await prisma.refreshToken.create({
      data: {
        token: refreshToken,
        userId: user.id,
        expiresAt: expiryDate,
      },
    });
    const response = NextResponse.json({
      success: true,
      user: {
        id: user.id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role,
        active: true,
      },
    });

    response.cookies.set("access_token", token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 15,
    });

    return response;
  } catch (error) {
    console.error("LOGIN ERROR:", error);

    return NextResponse.json(
      {
        success: false,
        error: String(error),
      },
      { status: 500 }
    );
  }
}
