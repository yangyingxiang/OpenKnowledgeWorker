'use client';

import { useMemo } from 'react';
import { Lightbulb } from 'lucide-react';
import type { KnowledgeItem } from '@/lib/api';

/** Knowledge items captured by the chat agent, grouped by PDD section. */
export function KnowledgeList({ knowledge }: { knowledge: KnowledgeItem[] }) {
  // Group knowledge by section
  const knowledgeBySection = useMemo(
    () =>
      knowledge.reduce(
        (acc, item) => {
          if (!acc[item.section]) acc[item.section] = [];
          acc[item.section].push(item);
          return acc;
        },
        {} as Record<string, KnowledgeItem[]>,
      ),
    [knowledge],
  );

  return (
    <>
      {knowledge.length === 0 ? (
        <div className="text-center py-12 text-[var(--okw-text-muted)]">
          <Lightbulb size={24} className="mx-auto mb-2 opacity-40" />
          <p className="text-sm">No knowledge items yet</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(knowledgeBySection).map(([section, items]) => (
            <div key={section}>
              <h4 className="text-xs font-semibold text-[var(--okw-text)] uppercase tracking-wider mb-2">
                {section}
              </h4>
              <div className="space-y-1.5">
                {items.map((item) => (
                  <div key={item.id} className="px-3 py-2 rounded-lg bg-[var(--okw-bg)] text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-[var(--okw-text)] text-xs leading-relaxed">
                        {item.content}
                      </p>
                      <span
                        className={`shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded ${
                          item.confidence === 'CONFIRMED'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {item.confidence}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
