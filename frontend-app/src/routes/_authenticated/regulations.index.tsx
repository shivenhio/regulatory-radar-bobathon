import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";
import { TopBar } from "@/components/layout/TopBar";
import { regulationsQuery } from "@/lib/api/regulations";
import { findingsQuery } from "@/lib/api/findings";
import { familyLabel, formatDate } from "@/lib/format";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ExternalLink } from "lucide-react";

export const Route = createFileRoute("/_authenticated/regulations/")({
  head: () => ({ meta: [{ title: "Regulations — Regulatory Radar" }] }),
  loader: async ({ context }) => {
    await Promise.all([
      context.queryClient.ensureQueryData(regulationsQuery()),
      context.queryClient.ensureQueryData(findingsQuery()),
    ]);
  },
  component: RegulationsPage,
});

function RegulationsPage() {
  const { data: regulations } = useSuspenseQuery(regulationsQuery());
  const { data: findings } = useSuspenseQuery(findingsQuery());
  const [family, setFamily] = useState("all");
  const [status, setStatus] = useState("all");

  const filtered = regulations.filter(
    (r) =>
      (family === "all" || r.family === family) && (status === "all" || r.status === status),
  );

  return (
    <>
      <TopBar title="Regulation explorer" chips={["EUR-Lex sync"]} />
      <div className="mx-auto max-w-7xl space-y-6 px-8 py-12">
        <div className="flex flex-wrap gap-2">
          <Select value={family} onValueChange={setFamily}>
            <SelectTrigger className="h-9 w-[160px] bg-navy-800 border-navy-600/30 text-xs">
              <SelectValue placeholder="Family" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All families</SelectItem>
              <SelectItem value="battery">EU Battery</SelectItem>
              <SelectItem value="reach">REACH</SelectItem>
              <SelectItem value="rohs">RoHS</SelectItem>
              <SelectItem value="weee">WEEE</SelectItem>
            </SelectContent>
          </Select>

          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="h-9 w-[140px] bg-navy-800 border-navy-600/30 text-xs">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="due">Due</SelectItem>
              <SelectItem value="upcoming">Upcoming</SelectItem>
              <SelectItem value="past">Past</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {filtered.map((r) => {
            const affected = findings.filter((f) => f.regulationId === r.id);
            const affectedCompanies = new Set(affected.map((f) => f.companyId)).size;
            const affectedProducts = new Set(affected.map((f) => f.productId)).size;
            return (
              <Link
                key={r.id}
                to="/regulations/$regulationId"
                params={{ regulationId: r.id }}
                className="block rounded-lg bg-navy-800 p-5 ring-1 ring-black/5 transition-colors hover:bg-navy-800/70"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-mono text-sm text-navy-100">{r.reference}</p>
                    <p className="mt-1 font-serif text-lg">{r.title}</p>
                  </div>
                  <span className="rounded bg-navy-950/50 px-2 py-1 text-[10px] uppercase tracking-wider text-navy-100/60 ring-1 ring-white/5">
                    {familyLabel(r.family)}
                  </span>
                </div>
                <p className="mt-3 text-sm text-navy-100/70">{r.summary}</p>
                <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-navy-100/50">
                  <span>Deadline: {formatDate(r.deadline)}</span>
                  <span>· {r.articles.length} articles</span>
                  <span>· {affectedCompanies} companies / {affectedProducts} products affected</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  {r.sourceUrls.map((u) => (
                    <span
                      key={u}
                      className="inline-flex items-center gap-1 text-navy-100/50"
                    >
                      <ExternalLink className="size-3" />
                      {new URL(u).hostname.replace("www.", "")}
                    </span>
                  ))}
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </>
  );
}
