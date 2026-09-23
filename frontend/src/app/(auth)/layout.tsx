import { AudioLines, ListChecks, UserRoundSearch } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { PrivacyBadge } from "@/components/brand/privacy-badge";
import { Wordmark } from "@/components/brand/wordmark";
import { LocaleToggle } from "@/components/shell/locale-toggle";

export default async function AuthLayout({ children }: { children: React.ReactNode }) {
  const t = await getTranslations("auth");
  const points = [
    { icon: AudioLines, text: t("heroPoints.langs") },
    { icon: UserRoundSearch, text: t("heroPoints.speakers") },
    { icon: ListChecks, text: t("heroPoints.tasks") },
  ];
  return (
    <div className="grid min-h-svh lg:grid-cols-[1.1fr_1fr]">
      {/* Left: indigo hero, only on large screens */}
      <aside className="bg-hero relative hidden overflow-hidden text-white lg:flex lg:flex-col">
        <div className="relative flex flex-1 flex-col justify-between p-12 xl:p-16">
          <Wordmark tone="dark" />
          <div className="max-w-xl">
            <h1 className="font-heading text-4xl leading-[1.1] font-bold text-balance xl:text-5xl">
              <span className="text-gradient">{t("heroTitle")}</span>
            </h1>
            <ul className="mt-10 space-y-4">
              {points.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center gap-3 text-white/80">
                  <span className="flex size-9 items-center justify-center rounded-xl bg-white/10 text-white ring-1 ring-white/15">
                    <Icon className="size-4" />
                  </span>
                  {text}
                </li>
              ))}
            </ul>
            {/* excerpt of a protocol as a teaser */}
            <figure className="text-ink mt-12 rounded-2xl bg-white p-5 shadow-[0_24px_60px_-20px_rgb(0_0_0/0.5)]">
              <div className="text-muted-foreground mb-3 flex items-center gap-2 text-xs">
                <span className="bg-speaker-0 size-2 rounded-full" />
                <span className="font-mono">01:12</span> · Айгерим Жумабаева
                <span className="bg-brand-soft text-primary ml-auto rounded-full px-2 py-0.5 text-[10px] font-semibold">
                  KZ
                </span>
              </div>
              <blockquote className="text-lg leading-relaxed font-medium">
                «Айбек,{" "}
                <mark className="marker-highlight rounded bg-transparent px-0.5 text-inherit">
                  техникалық тапсырманы ертеңге дейін дайында
                </mark>
                , жедел.»
              </blockquote>
              <figcaption className="text-muted-foreground mt-3 flex flex-wrap items-center gap-2 text-xs">
                <span className="bg-coral/10 text-coral rounded-full px-2 py-0.5 font-semibold">
                  critical
                </span>
                → Айбек Нуров · ИТ
              </figcaption>
            </figure>
          </div>
          <PrivacyBadge className="self-start border-white/20 bg-white/10 text-white" />
        </div>
      </aside>

      {/* Right: form */}
      <main className="bg-card flex flex-col">
        <div className="flex items-center justify-between p-6">
          <Wordmark className="lg:invisible" />
          <LocaleToggle persist={false} />
        </div>
        <div className="flex flex-1 items-center justify-center px-4 pb-16">
          <div className="animate-rise w-full max-w-sm">{children}</div>
        </div>
      </main>
    </div>
  );
}
