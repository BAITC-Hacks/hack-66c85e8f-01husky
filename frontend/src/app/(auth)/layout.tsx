import { AudioLines, ListChecks, UserRoundSearch } from "lucide-react";
import { getTranslations } from "next-intl/server";
import { OrnamentBand } from "@/components/brand/ornament";
import { PrivacyBadge } from "@/components/brand/privacy-badge";
import { SealStamp } from "@/components/brand/seal-stamp";
import { Wordmark } from "@/components/brand/wordmark";
import { LocaleToggle } from "@/components/shell/locale-toggle";

export default async function AuthLayout({ children }: { children: React.ReactNode }) {
  const t = await getTranslations("auth");
  const tb = await getTranslations("brand");
  const points = [
    { icon: AudioLines, text: t("heroPoints.langs") },
    { icon: UserRoundSearch, text: t("heroPoints.speakers") },
    { icon: ListChecks, text: t("heroPoints.tasks") },
  ];
  return (
    <div className="grid min-h-svh lg:grid-cols-[1.1fr_1fr]">
      {/* Left: ink panel, only on large screens */}
      <aside className="dark relative hidden overflow-hidden bg-background text-foreground lg:flex lg:flex-col">
        <OrnamentBand className="text-gold/40" />
        <div className="relative flex flex-1 flex-col justify-between p-12 xl:p-16">
          <Wordmark className="text-primary" />
          <div className="max-w-xl">
            <h1 className="font-heading text-4xl leading-[1.15] font-semibold text-balance xl:text-5xl">{t("heroTitle")}</h1>
            <ul className="mt-10 space-y-4">
              {points.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-center gap-3 text-muted-foreground">
                  <span className="flex size-9 items-center justify-center rounded-md border border-border text-gold">
                    <Icon className="size-4" />
                  </span>
                  {text}
                </li>
              ))}
            </ul>
            {/* excerpt of a protocol as a teaser */}
            <figure className="mt-12 rounded-lg border border-border bg-card/60 p-5 backdrop-blur">
              <div className="mb-3 flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
                <span className="size-2 rounded-full bg-speaker-0" /> 01:12 · Айгерим Жумабаева
                <span className="ml-auto rounded border border-border px-1.5 py-px">KZ</span>
              </div>
              <blockquote className="font-heading text-lg leading-relaxed">
                «Айбек, <mark className="marker-highlight rounded-sm bg-transparent px-0.5 text-foreground">техникалық тапсырманы ертеңге дейін дайында</mark>, жедел.»
              </blockquote>
              <figcaption className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span className="rounded-full bg-brick/15 px-2 py-0.5 font-medium text-brick">critical</span>
                → Айбек Нуров · ИТ
              </figcaption>
            </figure>
          </div>
          <PrivacyBadge className="self-start" />
        </div>
        <SealStamp label={tb("seal")} date="23.09.2026" className="absolute -right-6 bottom-24 size-44 opacity-60" />
        <OrnamentBand className="rotate-180 text-gold/40" />
      </aside>

      {/* Right: form */}
      <main className="paper-grain flex flex-col">
        <div className="flex items-center justify-between p-6">
          <Wordmark className="lg:invisible" />
          <LocaleToggle persist={false} />
        </div>
        <div className="flex flex-1 items-center justify-center px-4 pb-16">
          <div className="w-full max-w-sm animate-rise">{children}</div>
        </div>
      </main>
    </div>
  );
}
