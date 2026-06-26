import { useState } from "react";
import { MessageSquare, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { resendAlert } from "@/lib/api/alerts";
import { client, isMockMode } from "@/lib/api/client";

interface SendSmsButtonProps {
  label?: string;
  /** Passed as findingId when available; falls back to fetching the first finding. */
  findingId?: string;
  context?: string;
  className?: string;
}

/**
 * Fires POST /api/alerts/resend for a given finding (or the most recent one).
 * Shows a real success/error toast based on the backend response.
 */
export function SendSmsButton({
  label = "Send SMS via Twilio",
  findingId,
  context = "compliance alert",
  className = "",
}: SendSmsButtonProps) {
  const [pending, setPending] = useState(false);

  async function handleSend() {
    setPending(true);
    try {
      // Resolve findingId: use the prop if provided, otherwise fetch the first finding.
      let fid = findingId;
      if (!fid) {
        if (isMockMode) {
          fid = "mock-finding-1";
        } else {
          const findings = await client.get<{ id: string }[]>("/api/findings");
          fid = findings[0]?.id;
        }
      }
      if (!fid) throw new Error("No findings available to send an alert for.");

      const result = await resendAlert(fid, "en");
      toast.success("Alert dispatched via Twilio", {
        description: `Alert ID: ${result.alertId}  ·  context: ${context}`,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast.error("Twilio dispatch failed", { description: msg });
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      onClick={handleSend}
      disabled={pending}
      className={
        "inline-flex items-center gap-2 rounded-md bg-navy-600 px-3 py-2 text-sm font-medium text-navy-950 shadow-sm ring-1 ring-navy-600/40 transition-all hover:brightness-110 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 " +
        className
      }
    >
      {pending ? (
        <Loader2 className="size-4 animate-spin" />
      ) : (
        <MessageSquare className="size-4" />
      )}
      {pending ? "Dispatching…" : label}
    </button>
  );
}
