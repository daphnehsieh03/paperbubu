"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login, register } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { setToken } = useAuth();
  const router = useRouter();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [mode, setMode] = React.useState<"login" | "register">("login");
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const fn = mode === "login" ? login : register;
      const { access_token } = await fn(email, password);
      setToken(access_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{mode === "login" ? "Sign in" : "Create account"}</CardTitle>
          <p className="text-sm text-zinc-600">Research Paper Tracker</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Register"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-zinc-600">
            {mode === "login" ? (
              <>
                No account?{" "}
                <button type="button" className="text-zinc-900 underline" onClick={() => setMode("register")}>
                  Register
                </button>
              </>
            ) : (
              <>
                Have an account?{" "}
                <button type="button" className="text-zinc-900 underline" onClick={() => setMode("login")}>
                  Sign in
                </button>
              </>
            )}
          </p>
          <p className="mt-2 text-center">
            <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-800">
              Back to dashboard
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
