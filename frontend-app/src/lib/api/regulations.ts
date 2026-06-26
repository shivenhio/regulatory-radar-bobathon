import { queryOptions } from "@tanstack/react-query";
import { client, isMockMode, mockDelay } from "./client";
import type { Regulation } from "./types";
import mock from "../mock/regulations.json";

export async function getRegulations(): Promise<Regulation[]> {
  if (isMockMode) return mockDelay(mock as Regulation[]);
  return client.get<Regulation[]>("/api/regulations");
}

export async function getRegulation(id: string): Promise<Regulation | undefined> {
  if (isMockMode) return mockDelay((mock as Regulation[]).find((r) => r.id === id));
  return client.get<Regulation>(`/api/regulations/${id}`);
}

export const regulationsQuery = () =>
  queryOptions({ queryKey: ["regulations"], queryFn: getRegulations });

export const regulationQuery = (id: string) =>
  queryOptions({ queryKey: ["regulations", id], queryFn: () => getRegulation(id) });
