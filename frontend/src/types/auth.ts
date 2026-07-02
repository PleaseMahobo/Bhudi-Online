export type Role =
  | "super_admin"
  | "admin"
  | "manager"
  | "consultant"
  | "staff";

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: Role;
  active: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  user?: User;
  accessToken?: string;
  message?: string;
}

export interface JWTPayload {
  sub: string;
  email: string;
  role: Role;
  iat?: number;
  exp?: number;
}