import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { previewAlert, resendAlert } from "@/lib/api/alerts";
import type { Finding, Language } from "@/lib/api/types";
import { toast } from "sonner";
import { Send } from "lucide-react";

export function AlertPreviewForm({ finding }: { finding: Finding }) {
  const [language, setLanguage] = useState<Language>("en");

  const preview = useQuery({
    queryKey: ["alert-preview", finding.id, language],
    queryFn: () => previewAlert(finding.id, language),
  });

  const send = useMutation({
    mutationFn: () => resendAlert(finding.id, language),
    onSuccess: () => toast.success(`Alert dispatched via ${finding.alertChannel.toUpperCase()}`),
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-3 rounded-lg bg-navy-800 p-4 ring-1 ring-black/5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Preview alert message</p>
        <div className="flex gap-1 rounded bg-navy-950/50 p-1">
          {(["en", "de"] as const).map((l) => (
            <button
              key={l}
              onClick={() => setLanguage(l)}
              className={
                "px-2 py-1 text-[10px] font-semibold uppercase tracking-wider rounded transition-colors " +
                (language === l
                  ? "bg-navy-600 text-white"
                  : "text-navy-100/60 hover:text-white")
              }
            >
              {l}
            </button>
          ))}
        </div>
      </div>
      <div className="min-h-[80px] rounded bg-navy-950/40 p-3 font-mono text-xs text-navy-100/80">
        {preview.isLoading ? "Loading…" : preview.data?.message}
      </div>
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-widest text-navy-100/50">
          via {finding.alertChannel}
        </p>
        <button
          onClick={() => send.mutate()}
          disabled={send.isPending}
          className="inline-flex items-center gap-2 rounded bg-navy-600 px-3 py-1.5 text-xs font-medium text-white ring-1 ring-navy-600 transition-transform hover:brightness-110 active:scale-[0.98] disabled:opacity-50"
        >
          <Send className="size-3" />
          {send.isPending ? "Sending…" : "Send / Re-send"}
        </button>
      </div>
    </div>
  );
}
