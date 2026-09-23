import type { Metadata } from "next";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import { Link } from "@/i18n/navigation";
import "../globals.css";

export const metadata: Metadata = {
  title: "Автопротокол",
  description: "ИИ-протоколирование совещаний с фиксацией поручений",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "nav" });

  return (
    <html lang={locale}>
      <body className="min-h-screen bg-zinc-50 text-zinc-900 antialiased">
        <NextIntlClientProvider>
          <header className="border-b border-zinc-200 bg-white">
            <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3 text-sm">
              <Link href="/meetings" className="font-semibold">
                Автопротокол
              </Link>
              <Link href="/meetings">{t("meetings")}</Link>
              <Link href="/tasks">{t("tasks")}</Link>
              <Link href="/participants">{t("participants")}</Link>
              <span className="ml-auto flex gap-2 text-zinc-500">
                <Link href="/meetings" locale="ru">RU</Link>
                <span>/</span>
                <Link href="/meetings" locale="kk">KK</Link>
              </span>
              <Link href="/login">{t("login")}</Link>
            </nav>
          </header>
          <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
