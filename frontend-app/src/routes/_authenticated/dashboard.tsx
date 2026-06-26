import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { Suspense } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { KpiStrip } from "@/components/dashboard/KpiStrip";
import { FindingsTable } from "@/components/dashboard/FindingsTable";
import { DeadlineTimeline } from "@/components/dashboard/DeadlineTimeline";
import { companiesQuery } from "@/lib/api/companies";
import { productsQuery } from "@/lib/api/products";
import { regulationsQuery } from "@/lib/api/regulations";
import { findingsQuery, dedupeFindings, prioritizeByRisk } from "@/lib/api/findings";
import { Download } from "lucide-react";
import { SendSmsButton } from "@/components/alerts/SendSmsButton";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — Regulatory Radar" },
      {
        name: "description",
        content: "Compliance overview: open gaps, warnings, deadlines and alerts.",
      },
    ],
  }),
  loader: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(companiesQuery()),
      context.queryClient.ensureQueryData(productsQuery()),
      context.queryClient.ensureQueryData(regulationsQuery()),
      context.queryClient.ensureQueryData(findingsQuery()),
    ]);
  },
  component: DashboardPage,
});

function DashboardPage() {
  return (
    <>
      <TopBar
        title="Global Compliance Overview"
        chips={["EU Battery", "REACH", "RoHS", "WEEE"]}
        actions={
          <div className="flex items-center gap-2">
            <SendSmsButton context="dashboard summary" />
            <button className="flex items-center gap-2 rounded bg-navy-800 px-3 py-2 text-sm font-medium text-navy-100 shadow-sm ring-1 ring-navy-600/30 transition-transform hover:brightness-110 active:scale-[0.98]">
              <Download className="size-4" />
              Export report
            </button>
          </div>
        }
      />
      <div className="mx-auto max-w-7xl space-y-12 px-8 py-12">
        <Suspense fallback={<div className="h-24 animate-pulse rounded bg-navy-800/40" />}>
          <DashboardContent />
        </Suspense>
      </div>
    </>
  );
}

function DashboardContent() {
  const { data: companies } = useSuspenseQuery(companiesQuery());
  const { data: products } = useSuspenseQuery(productsQuery());
  const { data: regulations } = useSuspenseQuery(regulationsQuery());
  const { data: rawFindings } = useSuspenseQuery(findingsQuery());

  const findings = prioritizeByRisk(dedupeFindings(rawFindings));
  const red = findings.filter((f) => f.status === "red").length;
  const amber = findings.filter((f) => f.status === "amber").length;
  const green = findings.filter((f) => f.status === "green").length;

  return (
    <>
      <KpiStrip
        items={[
          { label: "Companies", value: String(companies.length).padStart(2, "0") },
          { label: "Products", value: String(products.length).padStart(2, "0") },
          { label: "Regulations", value: String(regulations.length).padStart(2, "0") },
          { label: "Red gaps", value: String(red).padStart(2, "0"), tone: "red" },
          { label: "Warnings", value: String(amber).padStart(2, "0"), tone: "amber" },
          { label: "Compliant", value: String(green).padStart(2, "0"), tone: "green" },
        ]}
      />

      <div className="grid items-start gap-8 lg:grid-cols-4">
        <section className="space-y-4 lg:col-span-3">
          <div className="flex items-center justify-between">
            <h3 className="font-serif text-xl font-medium">Critical findings</h3>
            <span className="text-xs text-navy-100/40">
              Prioritized by risk · deduped across sources
            </span>
          </div>
          <FindingsTable
            findings={findings}
            companies={companies}
            products={products}
            regulations={regulations}
          />
        </section>

        <aside className="space-y-4">
          <h3 className="font-serif text-xl font-medium">12-month timeline</h3>
          <DeadlineTimeline findings={findings} regulations={regulations} />
        </aside>
      </div>
    </>
  );
}
