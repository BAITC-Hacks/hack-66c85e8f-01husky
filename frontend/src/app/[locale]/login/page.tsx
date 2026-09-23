"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import { auth, ApiError } from "@/lib/api";

export default function LoginPage() {
  const t = useTranslations("auth");
  const router = useRouter();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await auth.login(email, password);
      router.push("/meetings");
    } catch (err) {
      setError(err instanceof ApiError ? String(err.detail) : String(err));
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-sm space-y-4">
      <h1 className="text-2xl font-semibold">{t("login")}</h1>
      <label className="block text-sm">
        {t("email")}
        <input className="mt-1 w-full rounded border px-3 py-2" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="block text-sm">
        {t("password")}
        <input className="mt-1 w-full rounded border px-3 py-2" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button className="w-full rounded bg-zinc-900 px-3 py-2 text-white" type="submit">
        {t("login")}
      </button>
      <p className="text-sm text-zinc-500">
        {t("noAccount")} <Link href="/register" className="underline">{t("register")}</Link>
      </p>
    </form>
  );
}
