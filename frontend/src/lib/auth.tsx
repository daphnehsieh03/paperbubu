"use client";

import * as React from "react";
import { apiBase, configureAuthApi, logoutSession } from "./api";

type AuthState = {
  token: string | null;
  authReady: boolean;
  setToken: (t: string | null) => void;
  signOut: () => Promise<void>;
};

const AuthContext = React.createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = React.useState<string | null>(null);
  const [authReady, setAuthReady] = React.useState(false);
  const tokenRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  React.useEffect(() => {
    configureAuthApi({
      getAccessToken: () => tokenRef.current,
      setAccessToken: (t) => setTokenState(t),
    });
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiBase()}/v1/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!cancelled && res.ok) {
          const d = (await res.json()) as { access_token: string };
          setTokenState(d.access_token);
        }
      } catch {
        /* offline */
      } finally {
        if (!cancelled) setAuthReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const setToken = React.useCallback((t: string | null) => {
    setTokenState(t);
  }, []);

  const signOut = React.useCallback(async () => {
    await logoutSession(tokenRef.current);
    setTokenState(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, authReady, setToken, signOut }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
