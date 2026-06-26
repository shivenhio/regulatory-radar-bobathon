import { useState } from "react";
import { MessageSquare, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface SendSmsButtonProps {
  label?: string;
  context?: string;
  className?: string;
}

/**
 * Stub button for the Twilio SMS gateway. Backend wiring will replace
 * the simulated delay with a POST to /api/alerts/send-sms.
 */
export function SendSmsButton({
  label = "Send SMS via Twilio",
  context = "compliance alert",
  className = "",
}: SendSmsButtonProps) {
  const [pending, setPending] = useState(false);

  async function handleSend() {
    setPending(true);
    try {
      // TODO: replace with real Twilio call once backend is wired
      // await client.post("/api/alerts/send-sms", { context });
      await new Promise((r) => setTimeout(r, 900));
      toast.success("SMS queued via Twilio", {
        description: `Test dispatch for ${context}. Hook up backend to deliver to a real phone.`,
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
