import { queryOptions } from "@tanstack/react-query";
import { client, isMockMode, mockDelay } from "./client";
import type { Finding, FindingStatus, RegulationFamily } from "./types";
import mock from "../mock/findings.json";

export interface FindingFilters {
  companyId?: string;
  productId?: string;
  regulationId?: string;
  family?: RegulationFamily;
  status?: FindingStatus;
  market?: string;
}

export async function getFindings(filters?: FindingFilters): Promise<Finding[]> {
  if (isMockMode) {
    let all = mock as Finding[];
    if (filters?.companyId) all = all.filter((f) => f.companyId === filters.companyId);
    if (filters?.productId) all = all.filter((f) => f.productId === filters.productId);
    if (filters?.regulationId) all = all.filter((f) => f.regulationId === filters.regulationId);
    if (filters?.status) all = all.filter((f) => f.status === filters.status);
    return mockDelay(all);
  }
  const qs = new URLSearchParams(filters as Record<string, string>).toString();
  return client.get<Finding[]>(`/api/findings${qs ? `?${qs}` : ""}`);
}

/**
 * Deduplicate findings sharing (company, product, regulation). Merges source URLs.
 */
export function dedupeFindings(findings: Finding[]): Finding[] {
  const map = new Map<string, Finding>();
  for (const f of findings) {
    const key = `${f.companyId}::${f.productId}::${f.regulationId}`;
    const existing = map.get(key);
    if (!existing) {
      map.set(key, { ...f, sourceUrls: [...new Set(f.sourceUrls)] });
    } else {
      existing.sourceUrls = [...new Set([...existing.sourceUrls, ...f.sourceUrls])];
      // Keep the most severe status: red > amber > green
      const sev = { red: 2, amber: 1, green: 0 } as const;
      if (sev[f.status] > sev[existing.status]) existing.status = f.status;
    }
  }
  return Array.from(map.values());
}

/**
 * Sort by risk: overdue first, then high-risk substance, then nearest deadline.
 */
export function prioritizeByRisk(findings: Finding[]): Finding[] {
  const now = Date.now();
  return [...findings].sort((a, b) => {
    const aOverdue = a.deadline && new Date(a.deadline).getTime() < now;
    const bOverdue = b.deadline && new Date(b.deadline).getTime() < now;
    if (aOverdue && !bOverdue) return -1;
    if (!aOverdue && bOverdue) return 1;
    const aHigh = a.highRiskSubstance ? 1 : 0;
    const bHigh = b.highRiskSubstance ? 1 : 0;
    if (aHigh !== bHigh) return bHigh - aHigh;
    const aT = a.deadline ? new Date(a.deadline).getTime() : Infinity;
    const bT = b.deadline ? new Date(b.deadline).getTime() : Infinity;
    return aT - bT;
  });
}

export const findingsQuery = (filters?: FindingFilters) =>
  queryOptions({
    queryKey: ["findings", filters ?? {}],
    queryFn: () => getFindings(filters),
  });
