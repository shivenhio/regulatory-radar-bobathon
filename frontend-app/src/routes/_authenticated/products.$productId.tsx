import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { TopBar } from "@/components/layout/TopBar";
import { productQuery } from "@/lib/api/products";
import { regulationsQuery } from "@/lib/api/regulations";
import { findingsQuery } from "@/lib/api/findings";
import { companiesQuery } from "@/lib/api/companies";
import { StatusPill } from "@/components/findings/StatusPill";
import { familyLabel, formatDate } from "@/lib/format";
import type { Finding, Regulation, RegulationFamily } from "@/lib/api/types";

export const Route = createFileRoute("/_authenticated/products/$productId")({
  loader: async ({ context, params }) => {
    const product = await context.queryClient.ensureQueryData(productQuery(params.productId));
    if (!product) throw notFound();
    await Promise.all([
      context.queryClient.ensureQueryData(regulationsQuery()),
      context.queryClient.ensureQueryData(findingsQuery({ productId: params.productId })),
      context.queryClient.ensureQueryData(companiesQuery()),
    ]);
  },
  head: ({ params }) => ({
    meta: [{ title: `Product ${params.productId} — Regulatory Radar` }],
  }),
  notFoundComponent: () => <div className="p-10 text-navy-100/60">Product not found.</div>,
  errorComponent: ({ error }) => <div className="p-10 text-status-red">{error.message}</div>,
  component: ProductDetailPage,
});

function ProductDetailPage() {
  const { productId } = Route.useParams();
  const { data: product } = useSuspenseQuery(productQuery(productId));
  const { data: regulations } = useSuspenseQuery(regulationsQuery());
  const { data: findings } = useSuspenseQuery(findingsQuery({ productId }));
  const { data: companies } = useSuspenseQuery(companiesQuery());

  if (!product) return null;
  const company = companies.find((c) => c.id === product.companyId);

  // Group findings by regulation family
  const regMap = new Map(regulations.map((r) => [r.id, r]));
  const byFamily = new Map<RegulationFamily, { reg: Regulation; finding: Finding }[]>();
  for (const f of findings) {
    const reg = regMap.get(f.regulationId);
    if (!reg) continue;
    const list = byFamily.get(reg.family) ?? [];
    list.push({ reg, finding: f });
    byFamily.set(reg.family, list);
  }

  return (
    <>
      <TopBar title={product.name} chips={[product.category, ...(product.batteryType ? [product.batteryType] : [])]} />
      <div className="mx-auto max-w-7xl space-y-8 px-8 py-12">
        <section className="grid gap-4 rounded-lg bg-navy-800 p-6 ring-1 ring-black/5 md:grid-cols-4">
          <Attr label="Company">
            {company && (
              <Link
                to="/companies/$companyId"
                params={{ companyId: company.id }}
                className="hover:text-white"
              >
                {company.name}
              </Link>
            )}
          </Attr>
          <Attr label="Category">{product.category}</Attr>
          <Attr label="Battery type">{product.batteryType ?? "—"}</Attr>
          <Attr label="Markets">{product.markets.join(" · ")}</Attr>
          <Attr label="Substances" className="md:col-span-4">
            {product.substances.join(", ")}
          </Attr>
        </section>

        <section className="space-y-6">
          <h2 className="font-serif text-2xl">Applicable regulations</h2>
          {Array.from(byFamily.entries()).map(([family, items]) => (
            <div key={family} className="space-y-3">
              <h3 className="text-[10px] font-semibold uppercase tracking-widest text-navy-100/50">
                {familyLabel(family)}
              </h3>
              <div className="grid gap-3 md:grid-cols-2">
                {items.map(({ reg, finding }) => (
                  <div
                    key={finding.id}
                    className="rounded-lg bg-navy-800 p-4 ring-1 ring-black/5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <Link
                          to="/regulations/$regulationId"
                          params={{ regulationId: reg.id }}
                          className="font-mono text-xs text-navy-100/70 hover:text-white"
                        >
                          {reg.reference}
                          {finding.articleRef ? ` ${finding.articleRef}` : ""}
                        </Link>
                        <p className="mt-1 text-sm">{finding.gapDescription}</p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <StatusPill status={finding.status} />
                        <span className="text-[10px] text-navy-100/50">
                          {formatDate(finding.deadline)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {byFamily.size === 0 && (
            <p className="text-sm text-navy-100/40">No regulations currently apply.</p>
          )}
        </section>
      </div>
    </>
  );
}

function Attr({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <p className="text-[10px] uppercase tracking-widest text-navy-100/50">{label}</p>
      <p className="mt-1 text-sm">{children}</p>
    </div>
  );
}
