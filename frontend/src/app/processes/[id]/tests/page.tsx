'use client';

import { useState, useEffect, useCallback, useRef, use } from 'react';
import { api, TestCase, TestRun } from '@/lib/api';
import { selectDisplayTestId, type RunMode } from '@/lib/tests/execState';
import { buildUploadMessage } from '@/lib/tests/format';
import { ChatSidebar } from '@/components/shared/ChatSidebar';
import { useTestRunner } from '@/components/tests/useTestRunner';
import { TestsToolbar } from '@/components/tests/TestsToolbar';
import { TestCaseList, TestCasesEmptyState } from '@/components/tests/TestCaseList';
import { LiveExecutionArea } from '@/components/tests/LiveExecutionArea';
import { TestRunHistory } from '@/components/tests/TestRunHistory';
import { CreateTestCaseDialog } from '@/components/tests/CreateTestCaseDialog';

export default function TestSuitePage({ params }: { params: Promise<{ id: string }> }) {
  const { id: processId } = use(params);

  /* ----- data state ----- */
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [selectedCases, setSelectedCases] = useState<Set<string>>(new Set());
  const [runMode, setRunMode] = useState<RunMode>('llm');
  const [chatHighlightTestId, setChatHighlightTestId] = useState<string | null>(null);
  const chatHighlightRef = useRef<HTMLDivElement>(null);
  const [pendingUploadMessage, setPendingUploadMessage] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  /* ----- loaders ----- */
  const loadTestCases = useCallback(async () => {
    try {
      setTestCases(await api.listTestCases(processId));
    } catch {
      /* swallow */
    }
  }, [processId]);

  const loadTestRuns = useCallback(async () => {
    try {
      setTestRuns(await api.listTestRuns(processId));
    } catch {
      /* swallow */
    }
  }, [processId]);

  useEffect(() => {
    loadTestCases();
    loadTestRuns();
  }, [loadTestCases, loadTestRuns]);

  /* ----- execution (SSE) ----- */
  const { exec, runTests, selectTest, stopTests, isRunning } = useTestRunner(
    processId,
    loadTestRuns,
  );

  const handleRunTests = () => {
    const caseIds = selectedCases.size > 0 ? Array.from(selectedCases) : undefined;
    runTests(runMode, caseIds);
  };

  /* ----- create / delete test case ----- */
  const handleCreate = async (data: Partial<TestCase>) => {
    await api.createTestCase(processId, data);
    loadTestCases();
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteTestCase(processId, id);
      loadTestCases();
    } catch {
      /* swallow */
    }
  };

  /* ----- bulk upload: JSONL imports directly; other files go to the chat agent for mapping ----- */
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleBulkUpload = async (file: File) => {
    setIsUploading(true);
    try {
      if (file.name.toLowerCase().endsWith('.jsonl')) {
        try {
          await api.bulkUploadTests(processId, file);
          await loadTestCases();
          return;
        } catch {
          /* not in the native format: fall back to the chat agent */
        }
      }
      const text = await file.text();
      setPendingUploadMessage(buildUploadMessage(file.name, text));
    } catch (err) {
      alert(`Upload failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  /* ----- selection ----- */
  const toggleCase = (id: string) => {
    setSelectedCases((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedCases.size === testCases.length) {
      setSelectedCases(new Set());
    } else {
      setSelectedCases(new Set(testCases.map((tc) => tc.id)));
    }
  };

  /* ----- derived state ----- */
  const displayTestId = selectDisplayTestId(exec);
  const currentTestName = testCases.find((tc) => tc.id === displayTestId)?.test_name;

  // Handle chat tool events for interactive test management
  const handleChatEvent = useCallback(
    (event: Record<string, unknown>) => {
      const name = event.name as string;

      // When agent reads a test case, highlight it in the list
      if (event.type === 'tool_call' && name === 'read_test_case') {
        const input = event.input as Record<string, string> | undefined;
        if (input?.test_name_or_id) {
          const tc = testCases.find(
            (t) => t.test_name === input.test_name_or_id || t.id === input.test_name_or_id,
          );
          if (tc) {
            setChatHighlightTestId(tc.id);
            setTimeout(
              () =>
                chatHighlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
              100,
            );
          }
        }
      }

      // When tests are created/modified/deleted, refresh and highlight
      if (event.type === 'tool_result') {
        if (
          [
            'create_test_case',
            'update_test_case',
            'delete_test_case',
            'bulk_create_tests',
          ].includes(name)
        ) {
          loadTestCases();
          // Highlight newly created/modified test
          try {
            const result = JSON.parse(event.result as string);
            if (result.id) {
              setChatHighlightTestId(result.id);
              setTimeout(
                () =>
                  chatHighlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
                200,
              );
            }
          } catch {}
        }
      }

      // Clear highlight when chat stream ends
      if (event.type === 'done') {
        setTimeout(() => setChatHighlightTestId(null), 3000);
      }
    },
    [loadTestCases, testCases],
  );

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <TestsToolbar
          runMode={runMode}
          onRunModeChange={setRunMode}
          isRunning={isRunning}
          onRun={handleRunTests}
          onStop={() => stopTests()}
          canRun={testCases.length > 0}
          selectedCount={selectedCases.size}
          isUploading={isUploading}
          onUploadClick={() => fileInputRef.current?.click()}
          onAddClick={() => setShowCreate(true)}
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.jsonl"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleBulkUpload(file);
          }}
        />

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {testCases.length === 0 ? (
            <TestCasesEmptyState
              onCreateClick={() => setShowCreate(true)}
              onUploadClick={() => fileInputRef.current?.click()}
              isUploading={isUploading}
            />
          ) : (
            <>
              <TestCaseList
                testCases={testCases}
                liveTests={exec.liveTests}
                displayTestId={displayTestId}
                chatHighlightTestId={chatHighlightTestId}
                chatHighlightRef={chatHighlightRef}
                selectedCases={selectedCases}
                onToggleCase={toggleCase}
                onToggleAll={toggleAll}
                onRowClick={(id) => {
                  setChatHighlightTestId(null);
                  if (exec.liveTests[id]) selectTest(id);
                }}
                onDelete={handleDelete}
              />

              {(Object.keys(exec.liveTests).length > 0 || isRunning) && (
                <LiveExecutionArea
                  exec={exec}
                  displayTestId={displayTestId}
                  testName={currentTestName}
                  runMode={runMode}
                />
              )}
            </>
          )}

          <TestRunHistory testRuns={testRuns} />
        </div>

        <CreateTestCaseDialog
          open={showCreate}
          onOpenChange={setShowCreate}
          onSubmit={handleCreate}
        />
      </div>

      <ChatSidebar
        processId={processId}
        context="tests"
        onChatEvent={handleChatEvent}
        pendingMessage={pendingUploadMessage}
        onPendingMessageSent={() => setPendingUploadMessage(null)}
      />
    </div>
  );
}
