import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { TopBar } from "@/components/layout/TopBar";
import { auditQuery } from "@/lib/api/audit";
import { formatDate } from "@/lib/format";
import { BellRing, FilePlus, FileEdit, AlertTriangle, CheckCircle2 } from "lucide-react";

const iconFor = {
  rule_updated: FileEdit,
  rule_added: FilePlus,
  gap_found: AlertTriangle,
  alert_sent: BellRing,
  finding_resolved: CheckCircle2,
} as const;

const colorFor = {
  rule_updated: "text-navy-600",
  rule_added: "text-navy-600",
  gap_found: "text-status-red",
  alert_sent: "text-navy-100",
  finding_resolved: "text-status-green",
} as const;

export const Route = createFileRoute("/_authenticated/audit")({
  head: () => ({ meta: [{ title: "Audit Log — Regulatory Radar" }] }),
  loader: async ({ context }) => {
    await context.queryClient.ensureQueryData(auditQuery());
  },
  component: AuditPage,
});

function AuditPage() {
  const { data: events } = useSuspenseQuery(auditQuery());
  return (
    <>
      <TopBar title="Audit log" chips={["Activity"]} />
      <div className="mx-auto max-w-4xl space-y-2 px-8 py-12">
        {events.map((e) => {
          const Icon = iconFor[e.kind];
          return (
            <div
              key={e.id}
              className="flex items-start gap-4 rounded-lg bg-navy-800 p-4 ring-1 ring-black/5"
            >
              <Icon className={"mt-1 size-4 shrink-0 " + colorFor[e.kind]} />
              <div className="flex-1">
                <p className="text-sm">{e.summary}</p>
                <p className="mt-1 text-[10px] uppercase tracking-widest text-navy-100/50">
                  {formatDate(e.timestamp)} · {e.kind.replace("_", " ")}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
