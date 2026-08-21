import { NextResponse } from 'next/server';

const ACCESS_COOKIE = 'access_token';
const REFRESH_COOKIE = 'refresh_token';
const ACCESS_MAX_AGE = 60 * 15;
const REFRESH_MAX_AGE = 60 * 60 * 24 * 30;

export function setAuthCookies(response: NextResponse, accessToken: string, refreshToken: string) {
  response.cookies.set({
    name: ACCESS_COOKIE,
    value: accessToken,
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: ACCESS_MAX_AGE,
  });
  response.cookies.set({
    name: REFRESH_COOKIE,
    value: refreshToken,
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: REFRESH_MAX_AGE,
  });
}

export function clearAuthCookies(response: NextResponse) {
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
}

export function copyBackendCookies(upstream: Response, response: NextResponse) {
  // Keep compatibility with the backend's Set-Cookie headers, but the proxy
  // also explicitly sets the cookies from the JSON token response. This avoids
  // relying on runtime-specific Response.headers.getSetCookie() behavior.
  const cookies = upstream.headers.getSetCookie?.() ?? [];
  for (const cookie of cookies) response.headers.append('set-cookie', cookie);
}
