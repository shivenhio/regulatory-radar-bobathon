import { queryOptions } from "@tanstack/react-query";
import { client, isMockMode, mockDelay } from "./client";
import type { Product } from "./types";
import mock from "../mock/products.json";

export async function getProducts(filters?: { companyId?: string }): Promise<Product[]> {
  if (isMockMode) {
    const all = mock as Product[];
    return mockDelay(filters?.companyId ? all.filter((p) => p.companyId === filters.companyId) : all);
  }
  const qs = filters?.companyId ? `?companyId=${filters.companyId}` : "";
  return client.get<Product[]>(`/api/products${qs}`);
}

export async function getProduct(id: string): Promise<Product | undefined> {
  if (isMockMode) return mockDelay((mock as Product[]).find((p) => p.id === id));
  return client.get<Product>(`/api/products/${id}`);
}

export const productsQuery = (filters?: { companyId?: string }) =>
  queryOptions({
    queryKey: ["products", filters ?? {}],
    queryFn: () => getProducts(filters),
  });

export const productQuery = (id: string) =>
  queryOptions({ queryKey: ["products", id], queryFn: () => getProduct(id) });
