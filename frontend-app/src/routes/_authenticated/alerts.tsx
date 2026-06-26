import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useState } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { alertsQuery } from "@/lib/api/alerts";
import { companiesQuery } from "@/lib/api/companies";
import { productsQuery } from "@/lib/api/products";
import { regulationsQuery } from "@/lib/api/regulations";
import { findingsQuery } from "@/lib/api/findings";
import { formatDate } from "@/lib/format";
import { AlertPreviewForm } from "@/components/alerts/AlertPreviewForm";
import { SendSmsButton } from "@/components/alerts/SendSmsButton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AlertDeliveryStatus } from "@/lib/api/types";

export const Route = createFileRoute("/_authenticated/alerts")({
  head: () => ({ meta: [{ title: "Alerts — Regulatory Radar" }] }),
  loader: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(alertsQuery()),
      context.queryClient.ensureQueryData(companiesQuery()),
      context.queryClient.ensureQueryData(productsQuery()),
      context.queryClient.ensureQueryData(regulationsQuery()),
      context.queryClient.ensureQueryData(findingsQuery()),
    ]);
  },
  component: AlertsPage,
});

const deliveryColor: Record<AlertDeliveryStatus, string> = {
  queued: "text-navy-100/60",
  sent: "text-navy-100",
  delivered: "text-status-green",
  failed: "text-status-red",
};

function AlertsPage() {
  const { data: alerts } = useSuspenseQuery(alertsQuery());
  const { data: companies } = useSuspenseQuery(companiesQuery());
  const { data: products } = useSuspenseQuery(productsQuery());
  const { data: regulations } = useSuspenseQuery(regulationsQuery());
  const { data: findings } = useSuspenseQuery(findingsQuery());

  const cMap = new Map(companies.map((c) => [c.id, c]));
  const pMap = new Map(products.map((p) => [p.id, p]));
  const rMap = new Map(regulations.map((r) => [r.id, r]));

  const [selectedFindingId, setSelectedFindingId] = useState<string>(findings[0]?.id ?? "");
  const selectedFinding = findings.find((f) => f.id === selectedFindingId);

  return (
    <>
      
      <TopBar
        title="Alerts center"
        chips={["Twilio gateway"]}
        actions={<SendSmsButton context="latest alert" />}
      />
      <div className="mx-auto grid max-w-7xl gap-8 px-8 py-12 lg:grid-cols-3">
        <section className="space-y-3 lg:col-span-2">
          <h3 className="font-serif text-xl">Dispatch history</h3>
          <div className="overflow-hidden rounded-lg bg-navy-800 ring-1 ring-black/5">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-navy-600/20 bg-navy-950/30 text-[10px] uppercase tracking-wider text-navy-100/50">
                  <th className="px-4 py-3 font-semibold">When</th>
                  <th className="px-4 py-3 font-semibold">Company / Product</th>
                  <th className="px-4 py-3 font-semibold">Regulation</th>
                  <th className="px-4 py-3 font-semibold">Channel</th>
                  <th className="px-4 py-3 font-semibold">Delivery</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-600/10 text-sm">
                {alerts.map((a) => (
                  <tr key={a.id} className="hover:bg-navy-600/5">
                    <td className="px-4 py-4 text-xs">{formatDate(a.sentAt)}</td>
                    <td className="px-4 py-4">
                      <div className="font-medium">{cMap.get(a.companyId)?.name}</div>
                      <div className="text-xs text-navy-100/50">
                        {pMap.get(a.productId)?.name}
                      </div>
                    </td>
                    <td className="px-4 py-4 font-mono text-xs">
                      {rMap.get(a.regulationId)?.reference}
                    </td>
                    <td className="px-4 py-4 text-xs uppercase tracking-wider">
                      {a.channel} · {a.language.toUpperCase()}
                    </td>
                    <td
                      className={
                        "px-4 py-4 text-xs font-semibold uppercase " +
                        deliveryColor[a.deliveryStatus]
                      }
                    >
                      {a.deliveryStatus}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="space-y-3">
          <h3 className="font-serif text-xl">Preview & re-send</h3>
          <Select value={selectedFindingId} onValueChange={setSelectedFindingId}>
            <SelectTrigger className="bg-navy-800 border-navy-600/30 text-xs">
              <SelectValue placeholder="Pick a finding" />
            </SelectTrigger>
            <SelectContent>
              {findings.map((f) => (
                <SelectItem key={f.id} value={f.id}>
                  {cMap.get(f.companyId)?.name} — {rMap.get(f.regulationId)?.reference}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {selectedFinding && <AlertPreviewForm finding={selectedFinding} />}
        </aside>
      </div>
    </>
  );
}
