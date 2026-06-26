interface Kpi {
  label: string;
  value: number | string;
  tone?: "default" | "red" | "amber" | "green";
}

const toneClass = {
  default: "text-navy-100",
  red: "text-status-red",
  amber: "text-status-amber",
  green: "text-status-green",
};

const toneLabelClass = {
  default: "text-navy-100/50",
  red: "text-status-red/70",
  amber: "text-status-amber/70",
  green: "text-status-green/70",
};

export function KpiStrip({ items }: { items: Kpi[] }) {
  return (
    <section className="grid grid-cols-2 gap-4 lg:grid-cols-6">
      {items.map((k) => (
        <div
          key={k.label}
          className="rounded-lg bg-navy-800 p-5 ring-1 ring-black/5"
        >
          <span
            className={
              "mb-1 block text-[10px] font-medium uppercase tracking-widest " +
              toneLabelClass[k.tone ?? "default"]
            }
          >
            {k.label}
          </span>
          <span
            className={
              "font-serif text-2xl font-semibold " + toneClass[k.tone ?? "default"]
            }
          >
            {k.value}
          </span>
        </div>
      ))}
    </section>
  );
}
