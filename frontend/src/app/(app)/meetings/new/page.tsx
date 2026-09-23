"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Bot, Mic, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { DatePicker } from "@/components/common/date-picker";
import { PageHeader } from "@/components/common/bits";
import { Field } from "@/components/common/field";
import { SEGMENT_ON } from "@/components/common/segment";
import { BotPane } from "@/components/new-meeting/bot-pane";
import { RecordPane } from "@/components/new-meeting/record-pane";
import { UploadPane } from "@/components/new-meeting/upload-pane";
import { ParticipantPicker } from "@/components/participants/participant-picker";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useCreateBotMeeting, useCreateLiveMeeting, useUploadMeeting } from "@/lib/api/queries/meetings";
import type { Locale } from "@/lib/api/types";
import { toISODate } from "@/lib/format";

const SOURCE_TAB = "flex-col gap-1 py-2 text-xs sm:flex-row sm:gap-2 sm:py-1 sm:text-sm";

export default function NewMeetingPage() {
  const t = useTranslations("newMeeting");
  const tb = useTranslations("meeting");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const upload = useUploadMeeting();
  const live = useCreateLiveMeeting();
  const bot = useCreateBotMeeting();

  const schema = z.object({
    title: z.string().trim().min(2, t("errors.title")),
    meeting_date: z.string().min(1, t("errors.date")),
    output_language: z.enum(["ru", "kk"]),
    participant_ids: z.array(z.number()).min(1, t("errors.participants")),
  });
  type Values = z.infer<typeof schema>;
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "",
      meeting_date: toISODate(new Date()),
      output_language: locale,
      participant_ids: [],
    },
  });
  const errors = form.formState.errors;

  /** Validate the shared card first; every source tab needs it. */
  const common = async (): Promise<Values | null> => {
    const ok = await form.trigger();
    if (!ok) {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return null;
    }
    return form.getValues();
  };
  const go = (id: number) => router.push(`/meetings/${id}`);

  return (
    <>
      <PageHeader
        eyebrow={
          <Link href="/meetings" className="hover:text-foreground inline-flex items-center gap-1">
            <ArrowLeft className="size-3" /> {tb("back")}
          </Link>
        }
        title={t("title")}
        subtitle={t("subtitle")}
      />

      <div className="grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        {/* Protocol card */}
        <section className="bg-card shadow-soft h-fit rounded-xl border p-5 sm:p-6 lg:sticky lg:top-24">
          <div className="text-primary mb-5 flex items-center justify-between text-xs font-semibold tracking-wide uppercase">
            <span>Kenes AI · Протокол</span>
            <span>№ ———</span>
          </div>
          <div className="grid gap-4">
            <Field label={t("fields.title")} htmlFor="title" error={errors.title?.message}>
              <Input
                id="title"
                placeholder={t("fields.titlePlaceholder")}
                className="font-heading h-10 text-base"
                aria-invalid={!!errors.title}
                {...form.register("title")}
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("fields.date")} error={errors.meeting_date?.message}>
                <Controller
                  control={form.control}
                  name="meeting_date"
                  render={({ field }) => (
                    <DatePicker value={field.value} onChange={(v) => field.onChange(v ?? "")} />
                  )}
                />
              </Field>
              <Field label={t("fields.outputLanguage")}>
                <Controller
                  control={form.control}
                  name="output_language"
                  render={({ field }) => (
                    <ToggleGroup
                      type="single"
                      variant="outline"
                      value={field.value}
                      onValueChange={(v) => v && field.onChange(v)}
                      className={`h-10 w-full ${SEGMENT_ON}`}
                    >
                      <ToggleGroupItem value="ru" className="h-10 flex-1">
                        Русский
                      </ToggleGroupItem>
                      <ToggleGroupItem value="kk" className="h-10 flex-1">
                        Қазақша
                      </ToggleGroupItem>
                    </ToggleGroup>
                  )}
                />
              </Field>
            </div>
            <Field label={t("fields.participants")} error={errors.participant_ids?.message}>
              <Controller
                control={form.control}
                name="participant_ids"
                render={({ field }) => (
                  <ParticipantPicker
                    value={field.value}
                    onChange={field.onChange}
                    invalid={!!errors.participant_ids}
                  />
                )}
              />
            </Field>
          </div>
        </section>

        {/* Source */}
        <section>
          <Tabs defaultValue="upload" className="gap-5">
            <TabsList className="grid h-auto w-full grid-cols-3 sm:h-11">
              <TabsTrigger value="upload" className={SOURCE_TAB}>
                <UploadCloud className="size-4" />
                <span className="max-w-full leading-tight whitespace-normal sm:truncate sm:whitespace-nowrap">
                  {t("tabs.upload")}
                </span>
              </TabsTrigger>
              <TabsTrigger value="record" className={SOURCE_TAB}>
                <Mic className="size-4" />
                <span className="max-w-full leading-tight whitespace-normal sm:truncate sm:whitespace-nowrap">
                  {t("tabs.record")}
                </span>
              </TabsTrigger>
              <TabsTrigger value="bot" className={SOURCE_TAB}>
                <Bot className="size-4" />
                <span className="max-w-full leading-tight whitespace-normal sm:truncate sm:whitespace-nowrap">
                  {t("tabs.bot")}
                </span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="upload">
              <UploadPane
                pending={upload.isPending}
                onSubmit={async (file) => {
                  const v = await common();
                  if (v) upload.mutate({ ...v, file }, { onSuccess: (m) => go(m.id) });
                }}
              />
            </TabsContent>

            <TabsContent value="record">
              <RecordPane
                createMeeting={async () => {
                  const v = await common();
                  if (!v) return null;
                  try {
                    return (await live.mutateAsync(v)).id;
                  } catch {
                    return null; // toasted by the global mutation handler
                  }
                }}
                onDone={go}
              />
            </TabsContent>

            <TabsContent value="bot">
              <BotPane
                pending={bot.isPending}
                onSubmit={async ({ platform, url }) => {
                  const v = await common();
                  if (!v) return;
                  bot.mutate(
                    {
                      title: v.title,
                      meeting_date: v.meeting_date,
                      participant_ids: v.participant_ids,
                      platform,
                      url,
                    },
                    {
                      onSuccess: (m) => {
                        toast.success(t("bot.sent"));
                        go(m.id);
                      },
                    },
                  );
                }}
              />
            </TabsContent>
          </Tabs>
          {Object.keys(errors).length > 0 && (
            <p className="text-coral mt-4 text-center text-xs lg:hidden">
              {Object.values(errors)[0]?.message}
            </p>
          )}
        </section>
      </div>
    </>
  );
}
