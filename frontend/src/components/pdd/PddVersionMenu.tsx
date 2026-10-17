'use client';

import { useState } from 'react';
import { ChevronDown, History } from 'lucide-react';
import type { PddVersion, PddVersionSummary } from '@/lib/api';

/** Dropdown in the SOP toolbar for switching between PDD versions. */
export function PddVersionMenu({
  pdd,
  versions,
  onSelectVersion,
}: {
  pdd: PddVersion;
  versions: PddVersionSummary[];
  onSelectVersion: (versionId: string) => Promise<void>;
}) {
  const [showVersions, setShowVersions] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setShowVersions(!showVersions)}
        className="flex items-center gap-1 px-2 py-1 rounded text-xs text-[var(--okw-text-muted)] hover:bg-white"
      >
        <History size={12} />v{pdd.version_number}
        <ChevronDown size={12} />
      </button>
      {showVersions && versions.length > 0 && (
        <div className="absolute right-0 top-full mt-1 bg-white rounded-lg shadow-lg border border-[var(--okw-border)] py-1 w-64 z-10 max-h-60 overflow-y-auto">
          {versions.map((v) => (
            <button
              key={v.id}
              onClick={async () => {
                await onSelectVersion(v.id);
                setShowVersions(false);
              }}
              className={`w-full text-left px-3 py-2 text-xs hover:bg-[var(--okw-bg)] ${
                pdd?.version_number === v.version_number ? 'bg-[var(--okw-primary-light)]' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">v{v.version_number}</span>
                <span className="text-[var(--okw-text-muted)]">{v.change_source}</span>
              </div>
              {v.change_summary && (
                <p className="text-[var(--okw-text-muted)] mt-0.5 truncate">{v.change_summary}</p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
