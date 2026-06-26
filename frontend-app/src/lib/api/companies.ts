import { queryOptions } from "@tanstack/react-query";
import { client, isMockMode, mockDelay } from "./client";
import type { Company } from "./types";
import mock from "../mock/companies.json";

export async function getCompanies(): Promise<Company[]> {
  if (isMockMode) return mockDelay(mock as Company[]);
  // TODO: replace with: return client.get<Company[]>("/api/companies");
  return client.get<Company[]>("/api/companies");
}

export async function getCompany(id: string): Promise<Company | undefined> {
  if (isMockMode) return mockDelay((mock as Company[]).find((c) => c.id === id));
  return client.get<Company>(`/api/companies/${id}`);
}

export const companiesQuery = () =>
  queryOptions({ queryKey: ["companies"], queryFn: getCompanies });

export const companyQuery = (id: string) =>
  queryOptions({ queryKey: ["companies", id], queryFn: () => getCompany(id) });
