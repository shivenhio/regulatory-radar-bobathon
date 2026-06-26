import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { TopBar } from "@/components/layout/TopBar";
import { productsQuery } from "@/lib/api/products";
import { companiesQuery } from "@/lib/api/companies";

export const Route = createFileRoute("/_authenticated/products/")({
  head: () => ({ meta: [{ title: "Products — Regulatory Radar" }] }),
  loader: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(productsQuery()),
      context.queryClient.ensureQueryData(companiesQuery()),
    ]);
  },
  component: ProductsPage,
});

function ProductsPage() {
  const { data: products } = useSuspenseQuery(productsQuery());
  const { data: companies } = useSuspenseQuery(companiesQuery());
  const cMap = new Map(companies.map((c) => [c.id, c]));

  return (
    <>
      <TopBar title="Products" chips={["Portfolio"]} />
      <div className="mx-auto max-w-7xl px-8 py-12">
        <div className="overflow-hidden rounded-lg bg-navy-800 ring-1 ring-black/5">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-navy-600/20 bg-navy-950/30 text-[10px] uppercase tracking-wider text-navy-100/50">
                <th className="px-4 py-3 font-semibold">Product</th>
                <th className="px-4 py-3 font-semibold">Company</th>
                <th className="px-4 py-3 font-semibold">Category</th>
                <th className="px-4 py-3 font-semibold">Substances</th>
                <th className="px-4 py-3 font-semibold">Markets</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-600/10 text-sm">
              {products.map((p) => (
                <tr key={p.id} className="hover:bg-navy-600/5">
                  <td className="px-4 py-4">
                    <Link
                      to="/products/$productId"
                      params={{ productId: p.id }}
                      className="font-medium hover:text-white"
                    >
                      {p.name}
                    </Link>
                    {p.batteryType && (
                      <div className="text-xs text-navy-100/50">{p.batteryType}</div>
                    )}
                  </td>
                  <td className="px-4 py-4 text-xs">
                    <Link
                      to="/companies/$companyId"
                      params={{ companyId: p.companyId }}
                      className="text-navy-100/70 hover:text-white"
                    >
                      {cMap.get(p.companyId)?.name ?? p.companyId}
                    </Link>
                  </td>
                  <td className="px-4 py-4 text-xs text-navy-100/70">{p.category}</td>
                  <td className="px-4 py-4 text-xs text-navy-100/70">
                    {p.substances.join(", ")}
                  </td>
                  <td className="px-4 py-4 text-xs text-navy-100/70">
                    {p.markets.join(" · ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
