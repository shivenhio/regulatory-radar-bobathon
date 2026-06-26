import { type ReactNode } from "react";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-navy-950 text-navy-100 font-sans">
      <Sidebar />
      <main className="pl-64">{children}</main>
    </div>
  );
}
