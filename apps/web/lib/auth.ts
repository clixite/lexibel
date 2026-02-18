/**
 * Auth — Re-exports from auth-core for backward compatibility.
 *
 * Previously this file contained the next-auth configuration.
 * Now it re-exports from auth-core.ts which uses localStorage-based JWT.
 */
export {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  decodeUser,
  getCurrentUser,
  isTokenValid,
  loginApi,
  refreshAccessToken,
  logout,
} from "./auth-core";

export type { AuthUser, LoginResponse } from "./auth-core";
