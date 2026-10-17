'use client';

import { useEffect, useState } from 'react';
import { BookOpen, Loader2 } from 'lucide-react';
import { api, DomainPack, Process } from '@/lib/api';

/** Lists the bundled domain packs; "Load example" creates a ready-to-explore process. */
export function ExamplePacks({ onInstalled }: { onInstalled: (process: Process) => void }) {
  const [packs, setPacks] = useState<DomainPack[]>([]);
  const [installing, setInstalling] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listDomainPacks()
      .then(setPacks)
      .catch(() => setPacks([]));
  }, []);

  if (packs.length === 0) return null;

  const install = async (pack: DomainPack) => {
    setInstalling(pack.id);
    setError(null);
    try {
      onInstalled(await api.installDomainPack(pack.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setInstalling(null);
    }
  };

  return (
    <section className="mb-8">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--okw-text-muted)] mb-3">
        Start from an example
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {packs.map((pack) => (
          <div
            key={pack.id}
            className="bg-white rounded-xl border border-dashed border-[var(--okw-primary)]/30 p-5 flex flex-col"
          >
            <div className="flex items-center gap-2 mb-2">
              <BookOpen size={16} className="text-[var(--okw-primary)]" />
              <span className="font-semibold text-[var(--okw-text)]">{pack.name}</span>
            </div>
            <span className="text-xs text-[var(--okw-text-muted)] bg-[var(--okw-bg)] px-2 py-0.5 rounded self-start mb-2">
              {pack.domain}
            </span>
            <p className="text-sm text-[var(--okw-text-muted)] line-clamp-3 flex-1">
              {pack.description}
            </p>
            <button
              onClick={() => install(pack)}
              disabled={installing !== null}
              className="mt-4 self-start flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--okw-primary)] text-[var(--okw-primary)] text-sm font-medium hover:bg-[var(--okw-primary-light)] transition-colors disabled:opacity-50"
            >
              {installing === pack.id && <Loader2 size={14} className="animate-spin" />}
              Load example
            </button>
          </div>
        ))}
      </div>
      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
    </section>
  );
}
