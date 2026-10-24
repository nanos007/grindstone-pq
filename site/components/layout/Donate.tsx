"use client";

import { useEffect, useRef, useState } from "react";
import { Bitcoin, Check, Copy } from "lucide-react";
import { BITCOIN_ADDRESS } from "@/lib/site";

/** Same mechanism as bitdome's Nav: a "Donate" pill that opens the address with a copy button. */
function useCopy() {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(BITCOIN_ADDRESS).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => {
        /* clipboard unavailable; the address stays selectable */
      },
    );
  }
  return [copied, copy] as const;
}

function AddressPanel({ copied, onCopy }: { copied: boolean; onCopy: () => void }) {
  return (
    <>
      <div className="flex items-center gap-2 mb-3">
        <Bitcoin size={15} className="text-primary shrink-0" aria-hidden />
        <p className="text-xs font-medium tracking-widest uppercase text-primary-active">Support with Bitcoin</p>
      </div>
      <div className="bg-surface-soft border border-hairline rounded-lg p-3 mb-3">
        <p className="text-[10px] font-medium tracking-widest uppercase text-muted mb-1">Bitcoin address</p>
        <p className="font-mono text-xs text-ink break-all leading-relaxed select-all">{BITCOIN_ADDRESS}</p>
      </div>
      <button
        onClick={onCopy}
        className={`w-full inline-flex items-center justify-center gap-2 text-sm font-medium rounded-lg px-4 py-2 min-h-[40px] transition-colors ${
          copied ? "bg-primary-active text-on-primary" : "bg-primary text-on-primary hover:bg-primary-active"
        }`}
      >
        {copied ? <Check size={15} /> : <Copy size={15} />}
        {copied ? "Copied!" : "Copy address"}
      </button>
      <p className="mt-3 text-xs text-muted leading-relaxed">
        Copy or open in any Bitcoin wallet. GRINDSTONE is a free, independent hobby project.
      </p>
    </>
  );
}

export function DonateDropdown() {
  const [open, setOpen] = useState(false);
  const [copied, copy] = useCopy();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 ml-2 text-sm font-medium rounded-full border border-primary text-primary-active hover:bg-surface-soft transition-colors"
        aria-label="Donate with Bitcoin — view address"
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <Bitcoin size={15} aria-hidden /> Donate
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Bitcoin donation address"
          className="absolute right-0 top-full mt-2 w-80 bg-canvas border border-hairline rounded-xl shadow-sm p-5 z-50"
        >
          <AddressPanel copied={copied} onCopy={copy} />
        </div>
      )}
    </div>
  );
}

export function MobileDonate() {
  const [copied, copy] = useCopy();
  return (
    <div className="border border-hairline rounded-xl p-4 mt-4">
      <AddressPanel copied={copied} onCopy={copy} />
    </div>
  );
}
