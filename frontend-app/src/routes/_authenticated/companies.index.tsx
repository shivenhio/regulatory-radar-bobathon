import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { TopBar } from "@/components/layout/TopBar";
import { companiesQuery } from "@/lib/api/companies";
import { findingsQuery } from "@/lib/api/findings";
import { StatusPill } from "@/components/findings/StatusPill";

export const Route = createFileRoute("/_authenticated/companies/")({
  head: () => ({
    meta: [{ title: "Companies — Regulatory Radar" }],
  }),
  loader: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(companiesQuery()),
      context.queryClient.ensureQueryData(findingsQuery()),
    ]);
  },
  component: CompaniesPage,
});

function CompaniesPage() {
  const { data: companies } = useSuspenseQuery(companiesQuery());
  const { data: findings } = useSuspenseQuery(findingsQuery());

  return (
    <>
      <TopBar title="Companies" chips={["Portfolio"]} />
      <div className="mx-auto max-w-7xl px-8 py-12">
        <div className="overflow-hidden rounded-lg bg-navy-800 ring-1 ring-black/5">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-navy-600/20 bg-navy-950/30 text-[10px] uppercase tracking-wider text-navy-100/50">
                <th className="px-4 py-3 font-semibold">Company</th>
                <th className="px-4 py-3 font-semibold">Markets</th>
                <th className="px-4 py-3 font-semibold">Preferred channel</th>
                <th className="px-4 py-3 font-semibold">Open gaps</th>
                <th className="px-4 py-3 font-semibold">Warnings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-600/10 text-sm">
              {companies.map((c) => {
                const own = findings.filter((f) => f.companyId === c.id);
                const red = own.filter((f) => f.status === "red").length;
                const amber = own.filter((f) => f.status === "amber").length;
                return (
                  <tr key={c.id} className="hover:bg-navy-600/5">
                    <td className="px-4 py-4">
                      <Link
                        to="/companies/$companyId"
                        params={{ companyId: c.id }}
                        className="font-medium hover:text-white"
                      >
                        {c.name}
                      </Link>
                    </td>
                    <td className="px-4 py-4 text-xs text-navy-100/70">
                      {c.markets.join(" · ")}
                    </td>
                    <td className="px-4 py-4 text-xs uppercase tracking-wider text-navy-100/60">
                      {c.preferredChannel} · {c.preferredLanguage.toUpperCase()}
                    </td>
                    <td className="px-4 py-4">
                      {red > 0 ? (
                        <StatusPill status="red" label={`${red} red`} />
                      ) : (
                        <span className="text-xs text-navy-100/40">0</span>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      {amber > 0 ? (
                        <StatusPill status="amber" label={`${amber} amber`} />
                      ) : (
                        <span className="text-xs text-navy-100/40">0</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
