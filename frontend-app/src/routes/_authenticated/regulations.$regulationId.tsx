import { createFileRoute, notFound } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { TopBar } from "@/components/layout/TopBar";
import { regulationQuery } from "@/lib/api/regulations";
import { findingsQuery } from "@/lib/api/findings";
import { companiesQuery } from "@/lib/api/companies";
import { familyLabel, formatDate } from "@/lib/format";
import { ExternalLink } from "lucide-react";

export const Route = createFileRoute("/_authenticated/regulations/$regulationId")({
  loader: async ({ context, params }) => {
    const reg = await context.queryClient.ensureQueryData(regulationQuery(params.regulationId));
    if (!reg) throw notFound();
    await Promise.all([
      context.queryClient.ensureQueryData(findingsQuery({ regulationId: params.regulationId })),
      context.queryClient.ensureQueryData(companiesQuery()),
    ]);
  },
  head: ({ params }) => ({
    meta: [{ title: `Regulation ${params.regulationId} — Regulatory Radar` }],
  }),
  notFoundComponent: () => <div className="p-10 text-navy-100/60">Regulation not found.</div>,
  errorComponent: ({ error }) => <div className="p-10 text-status-red">{error.message}</div>,
  component: RegulationDetailPage,
});

function RegulationDetailPage() {
  const { regulationId } = Route.useParams();
  const { data: reg } = useSuspenseQuery(regulationQuery(regulationId));
  const { data: findings } = useSuspenseQuery(findingsQuery({ regulationId }));
  const { data: companies } = useSuspenseQuery(companiesQuery());

  if (!reg) return null;

  const affectedCompanies = new Set(findings.map((f) => f.companyId));
  const affectedProducts = new Set(findings.map((f) => f.productId));
  const cMap = new Map(companies.map((c) => [c.id, c]));

  return (
    <>
      <TopBar title={reg.reference} chips={[familyLabel(reg.family), reg.status.toUpperCase()]} />
      <div className="mx-auto max-w-7xl space-y-8 px-8 py-12">
        <section className="rounded-lg bg-navy-800 p-6 ring-1 ring-black/5">
          <h2 className="font-serif text-2xl">{reg.title}</h2>
          <p className="mt-3 text-sm text-navy-100/70">{reg.summary}</p>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <Stat label="Deadline" value={formatDate(reg.deadline)} />
            <Stat label="Companies affected" value={String(affectedCompanies.size)} />
            <Stat label="Products affected" value={String(affectedProducts.size)} />
          </div>
          <div className="mt-4 flex flex-wrap gap-3 border-t border-navy-600/20 pt-4 text-xs">
            {reg.sourceUrls.map((u) => (
              <a
                key={u}
                href={u}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-navy-100/70 hover:text-white"
              >
                <ExternalLink className="size-3" />
                {u}
              </a>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="font-serif text-xl">Articles</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {reg.articles.map((a) => (
              <div key={a.ref} className="rounded-lg bg-navy-800 p-4 ring-1 ring-black/5">
                <p className="font-mono text-sm">{a.ref}</p>
                <p className="mt-1 font-medium">{a.title}</p>
                <p className="mt-1 text-xs text-navy-100/70">{a.description}</p>
                {a.deadline && (
                  <p className="mt-2 text-[10px] uppercase tracking-widest text-navy-100/50">
                    Deadline: {formatDate(a.deadline)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="font-serif text-xl">Affected portfolio</h3>
          <ul className="space-y-2 text-sm">
            {Array.from(affectedCompanies).map((cid) => (
              <li key={cid} className="rounded bg-navy-800 px-4 py-2 ring-1 ring-black/5">
                {cMap.get(cid)?.name ?? cid}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-widest text-navy-100/50">{label}</p>
      <p className="mt-1 font-serif text-xl">{value}</p>
    </div>
  );
}
