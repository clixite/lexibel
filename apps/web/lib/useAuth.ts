"use client";

import { useSession } from "next-auth/react";

export interface AuthContext {
  accessToken: string;
  tenantId: string;
  userId: string;
  email: string;
  role: string;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export function useAuth(): AuthContext {
  const { data: session, status } = useSession();
  const user = session?.user as any;

  return {
    accessToken: user?.accessToken || "",
    tenantId: user?.tenantId || "",
    userId: user?.id || "",
    email: user?.email || "",
    role: user?.role || "",
    isLoading: status === "loading",
    isAuthenticated: status === "authenticated" && !!user?.accessToken,
  };
}
