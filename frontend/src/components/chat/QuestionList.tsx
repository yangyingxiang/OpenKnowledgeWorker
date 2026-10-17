'use client';

import { HelpCircle } from 'lucide-react';
import type { Question } from '@/lib/api';

const priorityColor = (p: number) =>
  p === 1
    ? 'bg-red-100 text-red-700'
    : p === 2
      ? 'bg-orange-100 text-orange-700'
      : 'bg-blue-100 text-blue-700';

const statusColor = (s: string) =>
  s === 'OPEN'
    ? 'bg-yellow-100 text-yellow-700'
    : s === 'ANSWERED'
      ? 'bg-green-100 text-green-700'
      : 'bg-gray-100 text-gray-600';

/** Open / answered questions for subject-matter experts, with priority and status badges. */
export function QuestionList({ questions }: { questions: Question[] }) {
  return (
    <>
      {questions.length === 0 ? (
        <div className="text-center py-12 text-[var(--okw-text-muted)]">
          <HelpCircle size={24} className="mx-auto mb-2 opacity-40" />
          <p className="text-sm">No questions yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {questions.map((q) => (
            <div
              key={q.id}
              className="px-3 py-2.5 rounded-lg border border-[var(--okw-border)] bg-white"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono text-[var(--okw-text-muted)]">
                  {q.display_id}
                </span>
                <span
                  className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${priorityColor(q.priority)}`}
                >
                  P{q.priority}
                </span>
                <span
                  className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${statusColor(q.status)}`}
                >
                  {q.status}
                </span>
              </div>
              <p className="text-sm text-[var(--okw-text)]">{q.text}</p>
              {q.answer && (
                <div className="mt-2 pt-2 border-t border-[var(--okw-border)]">
                  <p className="text-xs text-[var(--okw-success)]">{q.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
