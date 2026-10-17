'use client';

import { useState, useEffect, useCallback, useRef, use } from 'react';
import { api, PddVersion, PddVersionSummary, Question } from '@/lib/api';
import { useSSE } from '@/lib/useSSE';
import { Play, Loader2, RefreshCw } from 'lucide-react';
import { lineDiff, mergeSection, extractSection, hasChanges } from '@/lib/pdd/diff';
import { PddViewer } from '@/components/pdd/PddViewer';
import { DiffOverlay, type PddEditInfo } from '@/components/pdd/DiffOverlay';
import { PddVersionMenu } from '@/components/pdd/PddVersionMenu';
import { ChatSidebar } from '@/components/shared/ChatSidebar';

export default function PddStudioPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: processId } = use(params);

  // PDD state
  const [pdd, setPdd] = useState<PddVersion | null>(null);
  const [versions, setVersions] = useState<PddVersionSummary[]>([]);

  // Questions — kept locally for DiffOverlay revert logic (mapping display_id → id)
  const [questions, setQuestions] = useState<Question[]>([]);

  // SSE stream for research (chat is handled by ChatSidebar)
  const research = useSSE();

  // PDD edit diff state
  const [pendingEdit, setPendingEdit] = useState<PddEditInfo | null>(null);
  const pddBeforeRef = useRef<string>('');
  const revertedRef = useRef(false); // prevents stale async calls from re-showing overlay after revert
  // Track all side effects during a stream for full revert
  const sideEffectsRef = useRef<{
    resolvedQuestions: string[]; // display_ids of resolved questions
    createdKnowledge: string[]; // UUIDs of created knowledge items
    createdQuestions: string[]; // display_ids of created questions
  }>({ resolvedQuestions: [], createdKnowledge: [], createdQuestions: [] });

  const loadPdd = useCallback(async () => {
    try {
      const data = await api.getCurrentPdd(processId);
      setPdd(data);
    } catch {
      /* no PDD yet */
    }
  }, [processId]);

  const loadQuestions = useCallback(async () => {
    try {
      setQuestions(await api.listQuestions(processId));
    } catch {}
  }, [processId]);

  const loadVersions = useCallback(async () => {
    try {
      setVersions(await api.listPddVersions(processId));
    } catch {}
  }, [processId]);

  useEffect(() => {
    loadPdd();
    loadQuestions();
    loadVersions();
  }, [loadPdd, loadQuestions, loadVersions]);

  // Research
  const handleResearch = () => {
    research.startStream(
      () => api.researchPdd(processId),
      (event) => {
        if (event.type === 'done') {
          loadPdd();
          loadQuestions();
          loadVersions();
        }
      },
    );
  };

  // Build diff preview from tool_call input (instant) or from before/after content (fallback)
  const showEditPreview = useCallback((input: Record<string, string>) => {
    const before = pddBeforeRef.current;
    if (!before) return;
    const sectionPath = input.section_path || 'full';
    const newContent = input.new_content || '';
    const reason = input.reason || 'SOP edit';

    const oldSectionLines = extractSection(before, sectionPath);
    const newSectionLines = newContent.split('\n');
    const diff = lineDiff(oldSectionLines, newSectionLines);
    if (!hasChanges(diff)) return;

    const afterContent =
      sectionPath === 'full' ? newContent : mergeSection(before, sectionPath, newContent);
    setPendingEdit({
      sectionPath,
      reason,
      beforeContent: before,
      afterContent,
      diff,
    });
  }, []);

  // Fetch updated PDD and show cumulative diff against the pre-edit snapshot
  const showDiffFallback = useCallback(async () => {
    if (revertedRef.current) return; // user already reverted — don't re-show
    const before = pddBeforeRef.current;
    if (!before) return;
    try {
      const newPdd = await api.getCurrentPdd(processId);
      if (revertedRef.current) return; // check again after async fetch
      setPdd(newPdd);
      if (!newPdd.content || before === newPdd.content) return;
      const oldLines = before.split('\n');
      const newLines = newPdd.content.split('\n');
      const diff = lineDiff(oldLines, newLines);
      if (!hasChanges(diff)) return;
      setPendingEdit({
        sectionPath: 'full',
        reason: 'SOP was updated',
        beforeContent: before,
        afterContent: newPdd.content,
        diff,
      });
    } catch {
      /* PDD fetch failed — ignore */
    }
  }, [processId]);

  // Handle SSE events forwarded from ChatSidebar for PDD-specific side effects.
  // The ChatSidebar calls onChatEvent for every SSE event from the stream.
  // We lazily capture the pre-edit PDD snapshot on the first PDD-edit tool_call,
  // and reset tracking state when the stream completes (done event).
  const handleChatEvent = useCallback(
    (event: Record<string, unknown>) => {
      // Instant path: compute diff from tool_call input (no API round-trip)
      if (event.type === 'tool_call') {
        const name = event.name as string;
        if (name === 'propose_pdd_edit' || name === 'edit_pdd_text') {
          // Capture PDD snapshot before the first edit in this stream
          if (!pddBeforeRef.current) {
            pddBeforeRef.current = pdd?.content || '';
            revertedRef.current = false;
            sideEffectsRef.current = {
              resolvedQuestions: [],
              createdKnowledge: [],
              createdQuestions: [],
            };
          }
          if (name === 'propose_pdd_edit') {
            try {
              showEditPreview(event.input as Record<string, string>);
            } catch {}
          }
        }
        if (name === 'resolve_question') {
          const input = event.input as Record<string, string> | undefined;
          if (input?.display_id) sideEffectsRef.current.resolvedQuestions.push(input.display_id);
        }
      }

      // Fast-reliable path: PDD was just saved to DB — fetch + diff immediately
      if (event.type === 'tool_result') {
        const name = event.name as string;
        if (name === 'propose_pdd_edit' || name === 'edit_pdd_text') {
          showDiffFallback();
        }
        if (name === 'write_to_knowledge') {
          try {
            const result = JSON.parse((event.result as string) || '{}');
            if (result.id) sideEffectsRef.current.createdKnowledge.push(result.id);
          } catch {}
        }
        if (name === 'create_question') {
          try {
            const result = JSON.parse((event.result as string) || '{}');
            if (result.display_id) sideEffectsRef.current.createdQuestions.push(result.display_id);
          } catch {}
          loadQuestions();
        }
        if (name === 'resolve_question') {
          loadQuestions();
        }
      }

      if (event.type === 'done') {
        showDiffFallback();
        loadVersions();
        loadQuestions();
        // Reset pddBeforeRef so next stream gets a fresh snapshot
        pddBeforeRef.current = '';
      }
    },
    [pdd?.content, showEditPreview, showDiffFallback, loadVersions, loadQuestions],
  );

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: PDD Viewer */}
      <div className="flex-1 flex flex-col bg-white border-r border-[var(--okw-border)] relative">
        {/* PDD toolbar */}
        <div className="px-4 py-2.5 border-b border-[var(--okw-border)] flex items-center gap-2 bg-[var(--okw-bg)]">
          <button
            onClick={handleResearch}
            disabled={research.isStreaming}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--okw-primary)] text-white text-xs font-medium hover:bg-[var(--okw-primary-dark)] transition-colors disabled:opacity-50"
          >
            {research.isStreaming ? (
              <>
                <Loader2 size={13} className="animate-spin" /> Ingesting Documents...
              </>
            ) : (
              <>
                <Play size={13} /> Ingest Documents
              </>
            )}
          </button>
          <button
            onClick={() => {
              loadPdd();
              loadVersions();
            }}
            className="p-1.5 rounded hover:bg-white transition-colors"
            title="Refresh SOP"
          >
            <RefreshCw size={14} className="text-[var(--okw-text-muted)]" />
          </button>
          <div className="flex-1" />
          {pdd && pdd.version_number > 0 && (
            <PddVersionMenu
              pdd={pdd}
              versions={versions}
              onSelectVersion={async (versionId) => {
                const full = await api.getPddVersion(processId, versionId);
                setPdd(full);
              }}
            />
          )}
        </div>

        {/* PDD content */}
        <div className="flex-1 overflow-y-auto p-6">
          {research.isStreaming || (research.streamText && !pdd?.content) ? (
            <div className="animate-fade-in">
              <div className="flex items-center gap-2 mb-4 text-[var(--okw-primary)]">
                <Loader2 size={16} className={research.isStreaming ? 'animate-spin' : ''} />
                <span className="text-sm font-medium">
                  {research.isStreaming
                    ? 'Researching documents...'
                    : 'Research complete. Refreshing...'}
                </span>
              </div>
              <div className="text-sm text-[var(--okw-text)] whitespace-pre-wrap leading-relaxed">
                {research.streamText}
              </div>
            </div>
          ) : pdd && pdd.content ? (
            <PddViewer content={pdd.content} />
          ) : (
            <div className="text-center py-20 text-[var(--okw-text-muted)]">
              <BookOpenIcon />
              <h3 className="text-lg font-semibold text-[var(--okw-text)] mt-4">No SOP yet</h3>
              <p className="text-sm mt-1 mb-4">
                Upload documents first, then click Ingest Documents to generate
              </p>
            </div>
          )}
        </div>

        {/* PDD Edit Diff Overlay */}
        {pendingEdit && (
          <DiffOverlay
            edit={pendingEdit}
            onAccept={() => {
              setPendingEdit(null);
              loadPdd();
              loadVersions();
            }}
            onRevert={async () => {
              revertedRef.current = true;
              try {
                const fx = sideEffectsRef.current;
                // Revert PDD content
                await api.updatePdd(processId, {
                  content: pendingEdit.beforeContent,
                  change_summary: 'Reverted: ' + pendingEdit.reason,
                });
                // Re-open resolved questions
                for (const displayId of fx.resolvedQuestions) {
                  const q = questions.find((q) => q.display_id === displayId);
                  if (q) {
                    try {
                      await api.updateQuestion(processId, q.id, { status: 'OPEN', answer: '' });
                    } catch {}
                  }
                }
                // Delete knowledge items created during this stream
                for (const knowledgeId of fx.createdKnowledge) {
                  try {
                    await api.deleteKnowledge(processId, knowledgeId);
                  } catch {}
                }
                // Delete questions created during this stream
                for (const displayId of fx.createdQuestions) {
                  const q = questions.find((q) => q.display_id === displayId);
                  if (q) {
                    try {
                      await api.deleteQuestion(processId, q.id);
                    } catch {}
                  }
                }
                sideEffectsRef.current = {
                  resolvedQuestions: [],
                  createdKnowledge: [],
                  createdQuestions: [],
                };
                setPendingEdit(null);
                loadPdd();
                loadVersions();
                loadQuestions();
              } catch (err) {
                console.error('Revert failed:', err);
                revertedRef.current = false;
              }
            }}
          />
        )}
      </div>

      {/* Right: Chat Sidebar */}
      <ChatSidebar processId={processId} context="sop" onChatEvent={handleChatEvent} />
    </div>
  );
}

function BookOpenIcon() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="mx-auto opacity-30"
    >
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  );
}
