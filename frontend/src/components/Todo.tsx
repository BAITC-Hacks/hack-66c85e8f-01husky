import { useTranslations } from "next-intl";

/** Placeholder for screens not built yet (spec section 8). Replace with the real page. */
export function Todo({ title, spec }: { title: string; spec: string }) {
  const t = useTranslations("common");
  return (
    <section className="space-y-2">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-zinc-500">{t("todo")}</p>
      <p className="text-xs text-zinc-400">Спека: раздел 8, экран «{spec}»</p>
    </section>
  );
}
