"use client";

import * as React from "react";

const TOKEN_KEY = "papertrail_token";

type AuthState = {
  token: string | null;
  setToken: (t: string | null) => void;
};

const AuthContext = React.createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = React.useState<string | null>(null);

  React.useEffect(() => {
    try {
      const t = localStorage.getItem(TOKEN_KEY);
      if (t) setTokenState(t);
    } catch {
      /* ignore */
    }
  }, []);

  const setToken = React.useCallback((t: string | null) => {
    setTokenState(t);
    try {
      if (t) localStorage.setItem(TOKEN_KEY, t);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  return <AuthContext.Provider value={{ token, setToken }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
