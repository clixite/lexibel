"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { AuthUser } from "./auth-core";
import {
  getAccessToken,
  getCurrentUser,
  isTokenValid,
  clearTokens,
  setTokens,
  loginApi,
  refreshAccessToken,
  logout as coreLogout,
} from "./auth-core";

interface AuthContextValue {
  /** The decoded user from the JWT, or null if not authenticated */
  user: AuthUser | null;
  /** The raw JWT access token */
  accessToken: string;
  /** Shortcut: user.tenantId or empty */
  tenantId: string;
  /** Shortcut: user.id or empty */
  userId: string;
  /** Shortcut: user.email or empty */
  email: string;
  /** Shortcut: user.role or empty */
  role: string;
  /** True while the initial token check is running */
  isLoading: boolean;
  /** True if the user is authenticated */
  isAuthenticated: boolean;
  /** Call to clear tokens and redirect to /login */
  logout: () => void;
  /** Call after a successful login to update context */
  onLoginSuccess: (accessToken: string, refreshToken: string) => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  accessToken: "",
  tenantId: "",
  userId: "",
  email: "",
  role: "",
  isLoading: true,
  isAuthenticated: false,
  logout: () => {},
  onLoginSuccess: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check token on mount
  useEffect(() => {
    const check = async () => {
      if (isTokenValid()) {
        setUser(getCurrentUser());
        setIsLoading(false);
        return;
      }

      // Try refresh
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        setUser(getCurrentUser());
      } else {
        clearTokens();
        setUser(null);
      }
      setIsLoading(false);
    };

    check();
  }, []);

  const logout = useCallback(() => {
    coreLogout();
    setUser(null);
  }, []);

  const onLoginSuccess = useCallback(
    (accessToken: string, refreshToken: string) => {
      setTokens(accessToken, refreshToken);
      setUser(getCurrentUser());
    },
    [],
  );

  const value = useMemo<AuthContextValue>(() => {
    const token = getAccessToken() || "";
    return {
      user,
      accessToken: user ? token : "",
      tenantId: user?.tenantId || "",
      userId: user?.id || "",
      email: user?.email || "",
      role: user?.role || "",
      isLoading,
      isAuthenticated: !!user,
      logout,
      onLoginSuccess,
    };
  }, [user, isLoading, logout, onLoginSuccess]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthContextValue {
  return useContext(AuthContext);
}
