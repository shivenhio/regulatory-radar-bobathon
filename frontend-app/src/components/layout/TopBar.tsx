import { type ReactNode } from "react";

interface TopBarProps {
  title: string;
  chips?: string[];
  actions?: ReactNode;
}

export function TopBar({ title, chips, actions }: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 border-b border-navy-600/20 bg-navy-950/80 px-8 py-4 backdrop-blur-md">
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-4">
          <h1 className="font-serif text-2xl font-bold leading-tight text-balance md:text-3xl">
            {title}
          </h1>
          {chips && chips.length > 0 && (
            <div className="hidden items-center gap-2 overflow-x-auto md:flex">
              {chips.map((c) => (
                <span
                  key={c}
                  className="rounded bg-navy-800 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider ring-1 ring-white/10"
                >
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
}
