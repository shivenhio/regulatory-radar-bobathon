import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ExternalLink, BellRing, ArrowUpDown, MessageSquare, Loader2 } from "lucide-react";
import { toast } from "sonner";
import type {
  Company,
  Finding,
  FindingStatus,
  Product,
  Regulation,
  RegulationFamily,
} from "@/lib/api/types";
import { StatusPill } from "@/components/findings/StatusPill";
import { formatDate, formatRelative, familyLabel } from "@/lib/format";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Props {
  findings: Finding[];
  companies: Company[];
  products: Product[];
  regulations: Regulation[];
  initialLimit?: number;
}

type SortKey = "deadline" | "status" | "company";

const statusRank: Record<FindingStatus, number> = { red: 0, amber: 1, green: 2 };

export function FindingsTable({
  findings,
  companies,
  products,
  regulations,
  initialLimit,
}: Props) {
  const [companyId, setCompanyId] = useState<string>("all");
  const [family, setFamily] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");
  const [market, setMarket] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortKey>("deadline");

  const companyMap = useMemo(() => new Map(companies.map((c) => [c.id, c])), [companies]);
  const productMap = useMemo(() => new Map(products.map((p) => [p.id, p])), [products]);
  const regulationMap = useMemo(
    () => new Map(regulations.map((r) => [r.id, r])),
    [regulations],
  );

  const markets = useMemo(() => {
    const s = new Set<string>();
    companies.forEach((c) => c.markets.forEach((m) => s.add(m)));
    return Array.from(s).sort();
  }, [companies]);

  const filtered = useMemo(() => {
    let rows = findings;
    if (companyId !== "all") rows = rows.filter((f) => f.companyId === companyId);
    if (family !== "all")
      rows = rows.filter((f) => regulationMap.get(f.regulationId)?.family === family);
    if (status !== "all") rows = rows.filter((f) => f.status === status);
    if (market !== "all")
      rows = rows.filter((f) => companyMap.get(f.companyId)?.markets.includes(market));

    rows = [...rows].sort((a, b) => {
      if (sortBy === "status") return statusRank[a.status] - statusRank[b.status];
      if (sortBy === "company") {
        return (companyMap.get(a.companyId)?.name ?? "").localeCompare(
          companyMap.get(b.companyId)?.name ?? "",
        );
      }
      const aT = a.deadline ? new Date(a.deadline).getTime() : Infinity;
      const bT = b.deadline ? new Date(b.deadline).getTime() : Infinity;
      return aT - bT;
    });

    return initialLimit ? rows.slice(0, initialLimit) : rows;
  }, [
    findings,
    companyId,
    family,
    status,
    market,
    sortBy,
    initialLimit,
    companyMap,
    regulationMap,
  ]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={companyId} onValueChange={setCompanyId}>
          <SelectTrigger className="h-9 w-[180px] bg-navy-800 border-navy-600/30 text-xs">
            <SelectValue placeholder="Company" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All companies</SelectItem>
            {companies.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={family} onValueChange={setFamily}>
          <SelectTrigger className="h-9 w-[140px] bg-navy-800 border-navy-600/30 text-xs">
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
            <SelectItem value="red">Red (non-compliant)</SelectItem>
            <SelectItem value="amber">Amber (warning)</SelectItem>
            <SelectItem value="green">Green (compliant)</SelectItem>
          </SelectContent>
        </Select>

        <Select value={market} onValueChange={setMarket}>
          <SelectTrigger className="h-9 w-[120px] bg-navy-800 border-navy-600/30 text-xs">
            <SelectValue placeholder="Market" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All markets</SelectItem>
            {markets.map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="ml-auto flex items-center gap-2 text-xs text-navy-100/50">
          <ArrowUpDown className="size-3" />
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortKey)}>
            <SelectTrigger className="h-9 w-[160px] bg-navy-800 border-navy-600/30 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="deadline">Sort: Deadline</SelectItem>
              <SelectItem value="status">Sort: Status</SelectItem>
              <SelectItem value="company">Sort: Company</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg bg-navy-800 ring-1 ring-black/5">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-navy-600/20 bg-navy-950/30">
              <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-navy-100/50">
                Company / Product
              </th>
              <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-navy-100/50">
                Regulation
              </th>
              <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-navy-100/50">
                Deadline
              </th>
              <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-navy-100/50">
                Status
              </th>
              <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-navy-100/50">
                Source
              </th>
              <th className="px-4 py-3 text-[10px] font-semibold uppercase tracking-wider text-navy-100/50">
                Alert
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-navy-600/10 text-sm">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-navy-100/40">
                  No findings match the current filters.
                </td>
              </tr>
            )}
            {filtered.map((f) => {
              const company = companyMap.get(f.companyId);
              const product = productMap.get(f.productId);
              const reg = regulationMap.get(f.regulationId);
              return (
                <tr key={f.id} className="transition-colors hover:bg-navy-600/5">
                  <td className="px-4 py-4">
                    <Link
                      to="/companies/$companyId"
                      params={{ companyId: f.companyId }}
                      className="font-medium hover:text-white"
                    >
                      {company?.name ?? f.companyId}
                    </Link>
                    <div className="text-xs text-navy-100/50">
                      <Link
                        to="/products/$productId"
                        params={{ productId: f.productId }}
                        className="hover:text-navy-100"
                      >
                        {product?.name ?? f.productId}
                      </Link>
                    </div>
                  </td>
                  <td className="px-4 py-4 font-mono text-xs">
                    <Link
                      to="/regulations/$regulationId"
                      params={{ regulationId: f.regulationId }}
                      className="hover:text-white"
                    >
                      {reg?.reference}
                      {f.articleRef ? ` ${f.articleRef}` : ""}
                    </Link>
                    <div className="font-sans text-[10px] uppercase tracking-wider text-navy-100/40">
                      {reg ? familyLabel(reg.family) : ""}
                    </div>
                  </td>
                  <td className="px-4 py-4 text-xs">
                    <div>{formatDate(f.deadline)}</div>
                    <div className="text-[10px] text-navy-100/40">
                      {formatRelative(f.deadline)}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <StatusPill status={f.status} />
                  </td>
                  <td className="px-4 py-4 text-xs">
                    {f.sourceUrls.slice(0, 2).map((u) => (
                      <a
                        key={u}
                        href={u}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-navy-100/60 hover:text-white"
                      >
                        <ExternalLink className="size-3" />
                        <span className="max-w-[120px] truncate">
                          {new URL(u).hostname.replace("www.", "")}
                        </span>
                      </a>
                    ))}
                  </td>
                  <td className="px-4 py-4 text-xs">
                    <RowAlertButton
                      companyName={company?.name ?? "company"}
                      alreadySent={f.alertSent}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RowAlertButton({
  companyName,
  alreadySent,
}: {
  companyName: string;
  alreadySent: boolean;
}) {
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(alreadySent);

  async function handleSend(e: React.MouseEvent) {
    e.stopPropagation();
    setPending(true);
    try {
      // TODO: replace with POST /api/alerts/send-sms { companyId, findingId }
      await new Promise((r) => setTimeout(r, 700));
      setSent(true);
      toast.success(`SMS queued for ${companyName}`, {
        description: "Twilio dispatch simulated — connect backend to deliver.",
      });
    } catch {
      toast.error("Twilio dispatch failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      onClick={handleSend}
      disabled={pending}
      className="inline-flex items-center gap-1 rounded bg-navy-600/20 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-navy-100 ring-1 ring-navy-600/40 transition-colors hover:bg-navy-600/40 disabled:opacity-60"
    >
      {pending ? (
        <Loader2 className="size-3 animate-spin" />
      ) : sent ? (
        <BellRing className="size-3 text-status-green" />
      ) : (
        <MessageSquare className="size-3" />
      )}
      {pending ? "Sending" : sent ? "Re-send" : "Alert"}
    </button>
  );
}
