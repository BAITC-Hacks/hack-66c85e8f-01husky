"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { toast } from "sonner";

const OFFLINE_ID = "connection-offline";

/** Sticky toast while the browser is offline; on reconnect, a short confirmation and a refetch. */
export function ConnectionStatus() {
  const t = useTranslations("errors.connection");
  const qc = useQueryClient();

  useEffect(() => {
    const offline = () =>
      toast.warning(t("offline"), { id: OFFLINE_ID, description: t("offlineHint"), duration: Infinity });
    const online = () => {
      toast.dismiss(OFFLINE_ID);
      toast.dismiss("error-network");
      toast.success(t("online"), { duration: 3000 });
      qc.invalidateQueries();
    };
    if (!navigator.onLine) offline();
    window.addEventListener("offline", offline);
    window.addEventListener("online", online);
    return () => {
      window.removeEventListener("offline", offline);
      window.removeEventListener("online", online);
    };
  }, [t, qc]);

  return null;
}
