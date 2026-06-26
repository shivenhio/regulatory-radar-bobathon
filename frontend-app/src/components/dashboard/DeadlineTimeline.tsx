import type { Finding, Regulation } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

interface Props {
  findings: Finding[];
  regulations: Regulation[];
  monthsAhead?: number;
}

const toneFor = (status: string) =>
  status === "red"
    ? "bg-status-red"
    : status === "amber"
      ? "bg-status-amber"
      : "bg-navy-600";

export function DeadlineTimeline({ findings, regulations, monthsAhead = 12 }: Props) {
  const regMap = new Map(regulations.map((r) => [r.id, r]));
  const cutoff = Date.now() + monthsAhead * 30 * 24 * 60 * 60 * 1000;
  const items = findings
    .filter((f) => f.deadline && new Date(f.deadline).getTime() <= cutoff)
    .sort(
      (a, b) =>
        new Date(a.deadline as string).getTime() - new Date(b.deadline as string).getTime(),
    )
    .slice(0, 6);

  return (
    <div className="relative space-y-6 overflow-hidden rounded-lg bg-navy-800 p-5 ring-1 ring-black/5">
      <div className="absolute bottom-6 left-7 top-6 w-px bg-navy-600/30" />
      {items.map((f) => {
        const reg = regMap.get(f.regulationId);
        return (
          <div key={f.id} className="relative flex items-start gap-4">
            <div
              className={
                "z-10 mt-1 size-4 shrink-0 rounded-full ring-4 ring-navy-800 " +
                toneFor(f.status)
              }
            />
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-navy-100/50">
                {formatDate(f.deadline)}
              </span>
              <p className="text-sm text-pretty">
                <span className="font-mono text-xs text-navy-100/60">
                  {reg?.reference}
                  {f.articleRef ? ` ${f.articleRef}` : ""}
                </span>{" "}
                — {f.gapDescription}
              </p>
            </div>
          </div>
        );
      })}
      {items.length === 0 && (
        <p className="text-sm text-navy-100/40">No deadlines in the next {monthsAhead} months.</p>
      )}
    </div>
  );
}
