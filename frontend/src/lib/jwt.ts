import { SignJWT, jwtVerify } from "jose";
import { JWTPayload } from "@/types/auth";

const secret = new TextEncoder().encode(
  process.env.JWT_SECRET!
);

export async function signAccessToken(payload: JWTPayload) {
  return await new SignJWT(payload as unknown as Record<string, unknown>)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("15m")
    .sign(secret);
}

export async function verifyAccessToken(token: string) {
  const { payload } = await jwtVerify(token, secret);
  return payload;
}