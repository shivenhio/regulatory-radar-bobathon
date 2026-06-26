import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Building2,
  Package,
  ScrollText,
  BellRing,
  History,
} from "lucide-react";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/companies", label: "Companies", icon: Building2 },
  { to: "/products", label: "Products", icon: Package },
  { to: "/regulations", label: "Regulations", icon: ScrollText },
  { to: "/alerts", label: "Alerts", icon: BellRing },
  { to: "/audit", label: "Audit Log", icon: History },
] as const;

export function Sidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside className="fixed inset-y-0 left-0 z-20 w-64 border-r border-navy-600/20 bg-navy-950/80 backdrop-blur-md">
      <div className="flex h-full flex-col">
        <div className="p-6">
          <Link to="/dashboard" className="block">
            <h2 className="font-serif text-lg font-bold tracking-tight text-navy-100">
              Regulatory Radar
            </h2>
            <p className="mt-1 text-[10px] uppercase tracking-widest text-navy-100/40">
              EU Compliance Console
            </p>
          </Link>
        </div>


        <nav className="flex-1 space-y-1 px-4">
          {nav.map((item) => {
            const active =
              item.to === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors " +
                  (active
                    ? "bg-navy-800 text-white ring-1 ring-white/10"
                    : "text-navy-100/70 hover:bg-navy-800/50 hover:text-white")
                }
              >
                <Icon className="size-4 shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
