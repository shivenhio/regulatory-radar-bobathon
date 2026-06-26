import type { FindingStatus } from "@/lib/api/types";

const styles: Record<FindingStatus, { cls: string; label: string }> = {
  red: {
    cls: "bg-status-red/10 text-status-red ring-status-red/20",
    label: "Non-Compliant",
  },
  amber: {
    cls: "bg-status-amber/10 text-status-amber ring-status-amber/20",
    label: "Warning",
  },
  green: {
    cls: "bg-status-green/10 text-status-green ring-status-green/20",
    label: "Compliant",
  },
};

export function StatusPill({
  status,
  label,
}: {
  status: FindingStatus;
  label?: string;
}) {
  const s = styles[status];
  return (
    <span
      className={
        "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 " +
        s.cls
      }
    >
      {label ?? s.label}
    </span>
  );
}
