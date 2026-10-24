import ReactMarkdown from "react-markdown";

/** One line of Markdown (bold, code) rendered without a wrapping paragraph. */
export default function InlineMd({ children }: { children: string }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <>{children}</>,
        strong: ({ children }) => <strong className="font-medium text-ink">{children}</strong>,
        code: ({ children }) => <code className="font-mono text-[0.85em] bg-surface-card px-1 rounded">{children}</code>,
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
