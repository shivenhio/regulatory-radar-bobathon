import { queryOptions } from "@tanstack/react-query";
import { client, isMockMode, mockDelay } from "./client";
import type { AuditEvent } from "./types";
import mock from "../mock/audit.json";

export async function getAuditEvents(): Promise<AuditEvent[]> {
  if (isMockMode) return mockDelay(mock as AuditEvent[]);
  return client.get<AuditEvent[]>("/api/audit");
}

export const auditQuery = () =>
  queryOptions({ queryKey: ["audit"], queryFn: getAuditEvents });
