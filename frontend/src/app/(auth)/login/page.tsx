"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Field } from "@/components/common/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MOCKING } from "@/lib/api/client";
import { useLogin } from "@/lib/api/queries/auth";

export default function LoginPage() {
  const t = useTranslations("auth");
  const router = useRouter();
  const login = useLogin();
  const schema = z.object({
    email: z.string().email(t("errors.email")),
    password: z.string().min(1, t("errors.password")),
  });
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: MOCKING ? { email: "admin@hattama.kz", password: "admin" } : { email: "", password: "" },
  });

  const onSubmit = form.handleSubmit((v) =>
    login.mutate(v, {
      onSuccess: () => {
        sessionStorage.removeItem("locale-synced");
        router.replace("/meetings");
      },
      onError: (e) => toast.error(e.message),
    }),
  );

  return (
    <>
      <h2 className="font-heading text-3xl font-semibold">{t("loginTitle")}</h2>
      <p className="mt-1.5 text-sm text-muted-foreground">{t("loginSubtitle")}</p>
      <form onSubmit={onSubmit} className="mt-8 grid gap-4">
        <Field label={t("email")} htmlFor="email" error={form.formState.errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" className="h-10" {...form.register("email")} />
        </Field>
        <Field label={t("password")} htmlFor="password" error={form.formState.errors.password?.message}>
          <Input id="password" type="password" autoComplete="current-password" className="h-10" {...form.register("password")} />
        </Field>
        <Button type="submit" size="lg" className="mt-2 h-10" disabled={login.isPending}>
          {login.isPending ? <Loader2 className="animate-spin" /> : null}
          {t("login")}
          <ArrowRight data-icon="inline-end" />
        </Button>
        {MOCKING && <p className="text-center font-mono text-[11px] text-muted-foreground">{t("mockHint")}</p>}
      </form>
      <p className="mt-8 text-center text-sm text-muted-foreground">
        {t("noAccount")}{" "}
        <Link href="/register" className="font-medium text-primary underline-offset-4 hover:underline">
          {t("register")}
        </Link>
      </p>
    </>
  );
}
