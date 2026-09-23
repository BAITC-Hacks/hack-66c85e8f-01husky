"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Field } from "@/components/common/field";
import { SEGMENT_ON } from "@/components/common/segment";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { setLocaleCookie } from "@/hooks/use-locale-switch";
import { useRegister } from "@/lib/api/queries/auth";
import type { Locale } from "@/lib/api/types";

export default function RegisterPage() {
  const t = useTranslations("auth");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const register = useRegister();
  const schema = z.object({
    name: z.string().trim().min(2, t("errors.name")),
    email: z.string().email(t("errors.email")),
    password: z.string().min(6, t("errors.password")),
    locale: z.enum(["ru", "kk"]),
  });
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", email: "", password: "", locale },
  });
  const errors = form.formState.errors;

  const onSubmit = form.handleSubmit((v) =>
    register.mutate(v, {
      onSuccess: (u) => {
        setLocaleCookie(u.locale);
        router.replace("/meetings");
        router.refresh();
      },
      onError: (e) => toast.error(e.message),
    }),
  );

  return (
    <>
      <h2 className="font-heading text-3xl font-semibold">{t("registerTitle")}</h2>
      <p className="text-muted-foreground mt-1.5 text-sm">{t("registerSubtitle")}</p>
      <form onSubmit={onSubmit} className="mt-8 grid gap-4">
        <Field label={t("name")} htmlFor="name" error={errors.name?.message}>
          <Input id="name" autoComplete="name" className="h-10" {...form.register("name")} />
        </Field>
        <Field label={t("email")} htmlFor="email" error={errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" className="h-10" {...form.register("email")} />
        </Field>
        <Field label={t("password")} htmlFor="password" error={errors.password?.message}>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            className="h-10"
            {...form.register("password")}
          />
        </Field>
        <Field label={t("locale")}>
          <Controller
            control={form.control}
            name="locale"
            render={({ field }) => (
              <ToggleGroup
                type="single"
                variant="outline"
                value={field.value}
                onValueChange={(v) => v && field.onChange(v)}
                className={`w-full ${SEGMENT_ON}`}
              >
                <ToggleGroupItem value="ru" className="flex-1">
                  Русский
                </ToggleGroupItem>
                <ToggleGroupItem value="kk" className="flex-1">
                  Қазақша
                </ToggleGroupItem>
              </ToggleGroup>
            )}
          />
        </Field>
        <Button type="submit" size="lg" className="mt-2 h-10" disabled={register.isPending}>
          {register.isPending ? <Loader2 className="animate-spin" /> : null}
          {t("register")}
          <ArrowRight data-icon="inline-end" />
        </Button>
      </form>
      <p className="text-muted-foreground mt-8 text-center text-sm">
        {t("haveAccount")}{" "}
        <Link href="/login" className="text-primary font-medium underline-offset-4 hover:underline">
          {t("login")}
        </Link>
      </p>
    </>
  );
}
