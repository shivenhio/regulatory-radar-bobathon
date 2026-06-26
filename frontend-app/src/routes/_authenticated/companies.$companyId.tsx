import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { TopBar } from "@/components/layout/TopBar";
import { companyQuery, companiesQuery } from "@/lib/api/companies";
import { productsQuery } from "@/lib/api/products";
import { regulationsQuery } from "@/lib/api/regulations";
import { findingsQuery } from "@/lib/api/findings";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusPill } from "@/components/findings/StatusPill";
import { formatDate } from "@/lib/format";
import { ExternalLink } from "lucide-react";

export const Route = createFileRoute("/_authenticated/companies/$companyId")({
  loader: async ({ context, params }) => {
    const company = await context.queryClient.ensureQueryData(companyQuery(params.companyId));
    if (!company) throw notFound();
    await Promise.all([
      context.queryClient.ensureQueryData(companiesQuery()),
      context.queryClient.ensureQueryData(productsQuery({ companyId: params.companyId })),
      context.queryClient.ensureQueryData(regulationsQuery()),
      context.queryClient.ensureQueryData(findingsQuery({ companyId: params.companyId })),
    ]);
  },
  head: ({ params }) => ({
    meta: [{ title: `Company ${params.companyId} — Regulatory Radar` }],
  }),
  notFoundComponent: () => (
    <div className="p-10 text-navy-100/60">Company not found.</div>
  ),
  errorComponent: ({ error }) => (
    <div className="p-10 text-status-red">{error.message}</div>
  ),
  component: CompanyDetailPage,
});

function CompanyDetailPage() {
  const { companyId } = Route.useParams();
  const { data: company } = useSuspenseQuery(companyQuery(companyId));
  const { data: products } = useSuspenseQuery(productsQuery({ companyId }));
  const { data: regulations } = useSuspenseQuery(regulationsQuery());
  const { data: findings } = useSuspenseQuery(findingsQuery({ companyId }));

  if (!company) return null;

  const regMap = new Map(regulations.map((r) => [r.id, r]));
  const productMap = new Map(products.map((p) => [p.id, p]));

  const red = findings.filter((f) => f.status === "red");
  const amber = findings.filter((f) => f.status === "amber");
  const green = findings.filter((f) => f.status === "green");

  return (
    <>
      <TopBar title={company.name} chips={company.markets} />
      <div className="mx-auto max-w-7xl space-y-8 px-8 py-12">
        <section className="grid gap-4 rounded-lg bg-navy-800 p-6 ring-1 ring-black/5 md:grid-cols-3">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-navy-100/50">
              Preferred channel
            </p>
            <p className="mt-1 text-sm uppercase">
              {company.preferredChannel} · {company.preferredLanguage.toUpperCase()}
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-widest text-navy-100/50">Contacts</p>
            <p className="mt-1 text-sm">
              {company.contacts.map((c) => (
                <span key={c.email} className="block">
                  {c.name} · <span className="text-navy-100/60">{c.email}</span>
                </span>
              ))}
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-widest text-navy-100/50">Products</p>
            <p className="mt-1 font-serif text-2xl">{products.length}</p>
          </div>
        </section>

        <Tabs defaultValue="gaps">
          <TabsList className="bg-navy-800">
            <TabsTrigger value="gaps">Current gaps ({red.length})</TabsTrigger>
            <TabsTrigger value="upcoming">Upcoming ({amber.length})</TabsTrigger>
            <TabsTrigger value="history">History ({green.length})</TabsTrigger>
            <TabsTrigger value="products">Products</TabsTrigger>
          </TabsList>

          <TabsContent value="gaps" className="mt-4 space-y-3">
            {red.length === 0 && <p className="text-sm text-navy-100/40">No open gaps.</p>}
            {red.map((f) => (
              <FindingCard key={f.id} f={f} reg={regMap.get(f.regulationId)} product={productMap.get(f.productId)} />
            ))}
          </TabsContent>

          <TabsContent value="upcoming" className="mt-4 space-y-3">
            {amber.length === 0 && <p className="text-sm text-navy-100/40">Nothing upcoming.</p>}
            {amber.map((f) => (
              <FindingCard key={f.id} f={f} reg={regMap.get(f.regulationId)} product={productMap.get(f.productId)} />
            ))}
          </TabsContent>

          <TabsContent value="history" className="mt-4 space-y-3">
            {green.length === 0 && <p className="text-sm text-navy-100/40">No resolved items.</p>}
            {green.map((f) => (
              <FindingCard key={f.id} f={f} reg={regMap.get(f.regulationId)} product={productMap.get(f.productId)} />
            ))}
          </TabsContent>

          <TabsContent value="products" className="mt-4">
            <div className="grid gap-3 md:grid-cols-2">
              {products.map((p) => (
                <Link
                  key={p.id}
                  to="/products/$productId"
                  params={{ productId: p.id }}
                  className="rounded-lg bg-navy-800 p-4 ring-1 ring-black/5 transition-colors hover:bg-navy-800/70"
                >
                  <p className="font-medium">{p.name}</p>
                  <p className="text-xs text-navy-100/50">
                    {p.category}
                    {p.batteryType ? ` · ${p.batteryType}` : ""}
                  </p>
                </Link>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}

function FindingCard({
  f,
  reg,
  product,
}: {
  f: import("@/lib/api/types").Finding;
  reg: import("@/lib/api/types").Regulation | undefined;
  product: import("@/lib/api/types").Product | undefined;
}) {
  return (
    <div className="rounded-lg bg-navy-800 p-4 ring-1 ring-black/5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-navy-100/60">
            {reg?.reference}
            {f.articleRef ? ` ${f.articleRef}` : ""}
            {product ? ` · ${product.name}` : ""}
          </p>
          <p className="mt-2 text-sm">{f.gapDescription}</p>
          <p className="mt-2 text-xs text-navy-100/50">
            Recommended fix: {f.recommendedFix}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <StatusPill status={f.status} />
          <span className="text-[10px] text-navy-100/50">{formatDate(f.deadline)}</span>
        </div>
      </div>
      {f.sourceUrls.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-3 border-t border-navy-600/20 pt-3 text-xs">
          {f.sourceUrls.map((u) => (
            <a
              key={u}
              href={u}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-navy-100/60 hover:text-white"
            >
              <ExternalLink className="size-3" />
              {new URL(u).hostname.replace("www.", "")}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
