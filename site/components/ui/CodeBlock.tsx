"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

/** Dark command block with a copy button. Comments (`# …`) are dimmed. */
export default function CodeBlock({ code, label }: { code: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    const commands = code
      .split("\n")
      .map((l) => l.replace(/\s+#.*$/, ""))
      .filter((l) => l.trim() && !l.trim().startsWith("#"))
      .join("\n");
    try {
      await navigator.clipboard.writeText(commands);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable (insecure context); the text stays selectable */
    }
  }

  return (
    <div className="relative bg-surface-dark rounded-xl">
      {label && <p className="px-5 pt-4 text-xs font-medium tracking-widest uppercase text-on-dark-soft">{label}</p>}
      <button
        onClick={copy}
        className="absolute top-3 right-3 inline-flex items-center gap-1.5 text-xs text-on-dark-soft hover:text-on-dark bg-surface-dark-elevated rounded-md px-2.5 py-1.5 transition-colors"
        aria-label="Copy commands"
      >
        {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : "Copy"}
      </button>
      <pre className="overflow-x-auto p-5 pr-24 text-sm leading-relaxed font-mono text-on-dark">
        {code.split("\n").map((line, i) => {
          const at = line.search(/\s#/);
          return (
            <div key={i}>
              {at >= 0 ? (
                <>
                  {line.slice(0, at)}
                  <span className="text-on-dark-soft">{line.slice(at)}</span>
                </>
              ) : (
                line || " "
              )}
            </div>
          );
        })}
      </pre>
    </div>
  );
}
