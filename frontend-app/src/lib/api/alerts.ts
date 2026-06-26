import { queryOptions } from "@tanstack/react-query";
import { client, isMockMode, mockDelay } from "./client";
import type { AlertRecord, Language } from "./types";
import mock from "../mock/alerts.json";

export async function getAlerts(): Promise<AlertRecord[]> {
  if (isMockMode) return mockDelay(mock as AlertRecord[]);
  return client.get<AlertRecord[]>("/api/alerts");
}

export async function previewAlert(
  findingId: string,
  language: Language,
): Promise<{ message: string }> {
  if (isMockMode) {
    const alert = (mock as AlertRecord[]).find((a) => a.findingId === findingId);
    const base =
      alert?.messagePreview ??
      "Regulatory Radar: a new compliance gap was detected. See dashboard for details.";
    const translated =
      language === "de"
        ? `[DE] ${base.replace("Regulatory Radar:", "Regulierungs-Radar:")}`
        : base;
    return mockDelay({ message: translated });
  }
  return client.post<{ message: string }>(`/api/alerts/preview`, { findingId, language });
}

export async function resendAlert(
  findingId: string,
  language: Language,
): Promise<{ ok: true; alertId: string }> {
  if (isMockMode) {
    return mockDelay({ ok: true as const, alertId: `a-${Date.now()}` });
  }
  return client.post<{ ok: true; alertId: string }>(`/api/alerts/resend`, { findingId, language });
}

export const alertsQuery = () =>
  queryOptions({ queryKey: ["alerts"], queryFn: getAlerts });
