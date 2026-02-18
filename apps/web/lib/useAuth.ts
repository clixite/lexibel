"use client";

import { useAuthContext } from "./AuthProvider";

export type { AuthUser } from "./auth-core";

export interface AuthContext {
  accessToken: string;
  tenantId: string;
  userId: string;
  email: string;
  role: string;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
  onLoginSuccess: (accessToken: string, refreshToken: string) => void;
}

export function useAuth(): AuthContext {
  return useAuthContext();
}
