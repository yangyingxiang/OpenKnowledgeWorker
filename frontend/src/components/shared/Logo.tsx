/** OpenKnowledgeWorker mark: a reader above an open book. Source: assets/logo.svg */
export function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="OpenKnowledgeWorker">
      <rect width="64" height="64" rx="15" fill="var(--okw-primary)" />
      <circle cx="32" cy="17.5" r="6.5" fill="#ffffff" />
      <path d="M9 29.5c8.5-3 16-2.2 21.6 2.6V52c-5.6-4.4-13.1-5.2-21.6-2.3z" fill="#ffffff" />
      <path
        d="M55 29.5c-8.5-3-16-2.2-21.6 2.6V52c5.6-4.4 13.1-5.2 21.6-2.3z"
        fill="#ffffff"
        fillOpacity={0.78}
      />
      <path
        d="M14 36.2c4.6-1.1 8.9-.7 12.6 1.3M14 41.4c4.6-1.1 8.9-.7 12.6 1.3"
        stroke="var(--okw-primary)"
        strokeWidth={2.2}
        strokeLinecap="round"
        fill="none"
        opacity={0.55}
      />
    </svg>
  );
}
