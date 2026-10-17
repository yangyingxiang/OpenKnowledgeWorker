'use client';

import { useState, useEffect, useCallback, useRef, use, useMemo } from 'react';
import { api, CodeProject, CodeProjectWithFiles, CodeFileSummary } from '@/lib/api';
import { useSSE } from '@/lib/useSSE';
import { buildTree, parentDirs } from '@/lib/code/fileTree';
import { ChatSidebar } from '@/components/shared/ChatSidebar';
import { CodeToolbar, type TestOutputSummary } from '@/components/code/CodeToolbar';
import { FileTreePanel } from '@/components/code/FileTreePanel';
import { CodeViewer } from '@/components/code/CodeViewer';

// ── Main page ──
export default function CodeAgentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: processId } = use(params);

  // State
  const [projects, setProjects] = useState<CodeProject[]>([]);
  const [activeProject, setActiveProject] = useState<CodeProjectWithFiles | null>(null);
  const [fileSummaries, setFileSummaries] = useState<CodeFileSummary[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [selectedFileContent, setSelectedFileContent] = useState<string>('');
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(
    new Set(['engine', 'engine/steps', 'tests']),
  );

  // Line highlighting (set by chat navigation)
  const [highlightLines, setHighlightLines] = useState<{ start: number; end: number } | null>(null);
  const highlightRef = useRef<HTMLDivElement>(null);

  // Agent activity
  const [agentPhase, setAgentPhase] = useState<string>('');
  const [testOutput, setTestOutput] = useState<TestOutputSummary | null>(null);
  const [filesWritten, setFilesWritten] = useState<string[]>([]);

  const sse = useSSE();

  // Select a file
  const handleSelectFile = async (
    path: string,
    projectId?: string,
    summariesOverride?: CodeFileSummary[],
  ) => {
    setSelectedFilePath(path);
    setHighlightLines(null);
    const pid = projectId || activeProject?.id;
    const sums = summariesOverride || fileSummaries;
    if (!pid) return;
    const summary = sums.find((f) => f.file_path === path);
    if (!summary) return;
    try {
      const file = await api.getProjectFile(processId, pid, summary.id);
      setSelectedFileContent(file.content);
    } catch {
      setSelectedFileContent('// Error loading file');
    }
  };

  // Load initial data
  const loadData = useCallback(async () => {
    try {
      const projs = await api.listCodingProjects(processId);
      setProjects(projs);
      if (projs.length > 0 && !activeProject) {
        const latest = projs[0];
        const full = await api.getCodingProject(processId, latest.id);
        setActiveProject(full);
        const summaries = await api.getProjectFiles(processId, latest.id);
        setFileSummaries(summaries);
        if (summaries.length > 0 && !selectedFilePath) {
          // Auto-select first source file
          const first = summaries.find((f) => f.file_type === 'source') || summaries[0];
          handleSelectFile(first.file_path, latest.id, summaries);
        }
      }
    } catch {}
  }, [processId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Toggle directory expand/collapse
  const toggleDir = (path: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  // Start coding agent
  const handleStart = () => {
    setTestOutput(null);
    setFilesWritten([]);
    setAgentPhase('planning');

    sse.startStream(
      () => api.startCodingAgent(processId),
      (event) => {
        if (event.type === 'status') {
          const phase = event.status as string;
          setAgentPhase(phase);
        }

        if (event.type === 'file_written') {
          const path = event.path as string;
          setFilesWritten((prev) => [...new Set([...prev, path])]);
        }

        if (event.type === 'test_output') {
          setTestOutput({
            passed: event.passed as number,
            failed: event.failed as number,
            errors: event.errors as number,
            output: event.output as string,
          });
        }

        if (event.type === 'done') {
          const projectId = event.project_id as string;
          setAgentPhase((event.status as string) || 'complete');
          // Reload project data
          (async () => {
            try {
              const full = await api.getCodingProject(processId, projectId);
              setActiveProject(full);
              const summaries = await api.getProjectFiles(processId, projectId);
              setFileSummaries(summaries);
              if (summaries.length > 0) {
                const first =
                  summaries.find(
                    (f) => f.file_type === 'source' && f.file_path.includes('engine'),
                  ) || summaries[0];
                handleSelectFile(first.file_path, projectId, summaries);
              }
              const projs = await api.listCodingProjects(processId);
              setProjects(projs);
            } catch {}
          })();
        }

        if (event.type === 'error') {
          setAgentPhase('error');
        }
      },
    );
  };

  // Build file tree
  const fileTree = useMemo(() => buildTree(fileSummaries), [fileSummaries]);

  // Expand all parent directories for a given file path in the tree
  const expandParentDirs = useCallback((filePath: string) => {
    const dirs = parentDirs(filePath);
    if (dirs.length === 0) return;
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      for (const dir of dirs) next.add(dir);
      return next;
    });
  }, []);

  // Navigate to a file and optionally highlight lines
  const navigateToFile = useCallback(
    (filePath: string, lineStart?: number, lineEnd?: number) => {
      const pid = activeProject?.id;
      if (!pid) return;
      expandParentDirs(filePath);
      const summary = fileSummaries.find((f) => f.file_path === filePath);
      if (summary) {
        setSelectedFilePath(filePath);
        api.getProjectFile(processId, pid, summary.id).then((f) => {
          setSelectedFileContent(f.content);
          if (lineStart) {
            setHighlightLines({ start: lineStart, end: lineEnd || lineStart });
            // Scroll after content renders
            setTimeout(
              () => highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
              100,
            );
          } else {
            setHighlightLines(null);
          }
        });
      } else {
        // File list may be stale — reload first
        api.getProjectFiles(processId, pid).then((sums) => {
          setFileSummaries(sums);
          const s = sums.find((f: CodeFileSummary) => f.file_path === filePath);
          if (s) {
            setSelectedFilePath(filePath);
            api.getProjectFile(processId, pid, s.id).then((f) => {
              setSelectedFileContent(f.content);
              if (lineStart) {
                setHighlightLines({ start: lineStart, end: lineEnd || lineStart });
                setTimeout(
                  () =>
                    highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
                  100,
                );
              } else {
                setHighlightLines(null);
              }
            });
          }
        });
      }
    },
    [activeProject?.id, processId, fileSummaries, expandParentDirs],
  );

  // Handle chat tool events for interactive code updates
  const handleChatEvent = useCallback(
    (event: Record<string, unknown>) => {
      const name = event.name as string;
      const pid = activeProject?.id;

      // When agent reads a file, navigate to it so user sees what's being discussed
      if (event.type === 'tool_call') {
        if (name === 'read_code_file') {
          const input = event.input as Record<string, string> | undefined;
          if (input?.file_path) navigateToFile(input.file_path);
        }
        if (name === 'navigate_to_file') {
          const input = event.input as Record<string, unknown> | undefined;
          if (input?.file_path) {
            navigateToFile(
              input.file_path as string,
              input.line_start as number | undefined,
              input.line_end as number | undefined,
            );
          }
        }
      }

      if (event.type === 'tool_result') {
        if (name === 'update_code_file' && pid) {
          try {
            const result = JSON.parse(event.result as string);
            if (result.success) {
              api.getProjectFiles(processId, pid).then((sums) => {
                setFileSummaries(sums);
                if (result.file_path === selectedFilePath) {
                  const s = sums.find((f: CodeFileSummary) => f.file_path === result.file_path);
                  if (s)
                    api
                      .getProjectFile(processId, pid, s.id)
                      .then((f) => setSelectedFileContent(f.content));
                }
              });
            }
          } catch {}
        }

        // After navigate_to_file result, also apply line highlights from the result
        if (name === 'navigate_to_file') {
          try {
            const result = JSON.parse(event.result as string);
            if (result.line_start) {
              setHighlightLines({
                start: result.line_start,
                end: result.line_end || result.line_start,
              });
              setTimeout(
                () => highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
                100,
              );
            }
          } catch {}
        }

        // When chat triggers the coding agent, start the SSE stream
        if (name === 'start_coding_agent') {
          try {
            const result = JSON.parse(event.result as string);
            if (result.success) {
              handleStart();
            }
          } catch {}
        }
      }
    },
    [activeProject?.id, processId, selectedFilePath, navigateToFile, handleStart],
  );

  const selectProject = async (pid: string) => {
    try {
      const full = await api.getCodingProject(processId, pid);
      setActiveProject(full);
      const summaries = await api.getProjectFiles(processId, pid);
      setFileSummaries(summaries);
      if (summaries.length > 0) {
        handleSelectFile(summaries[0].file_path, pid, summaries);
      }
    } catch {}
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <CodeToolbar
        onRefresh={loadData}
        agentPhase={agentPhase}
        isStreaming={sse.isStreaming}
        iteration={activeProject?.iteration}
        testOutput={testOutput}
        projects={projects}
        activeProjectId={activeProject?.id}
        onSelectProject={selectProject}
        downloadUrl={activeProject ? api.downloadProject(processId, activeProject.id) : null}
      />

      {/* Main 2-column layout + ChatSidebar */}
      <div className="flex-1 flex overflow-hidden">
        <FileTreePanel
          fileTree={fileTree}
          fileCount={fileSummaries.length}
          selectedPath={selectedFilePath}
          onSelect={(path) => handleSelectFile(path)}
          expandedDirs={expandedDirs}
          toggleDir={toggleDir}
          isStreaming={sse.isStreaming}
          filesWritten={filesWritten}
        />

        <CodeViewer
          selectedFilePath={selectedFilePath}
          fileVersion={fileSummaries.find((f) => f.file_path === selectedFilePath)?.version}
          content={selectedFileContent}
          highlightLines={highlightLines}
          highlightRef={highlightRef}
          onClearHighlight={() => setHighlightLines(null)}
          isStreaming={sse.isStreaming}
          hasFiles={fileSummaries.length > 0}
        />

        {/* Chat Sidebar */}
        <ChatSidebar processId={processId} context="code" onChatEvent={handleChatEvent} />
      </div>
    </div>
  );
}
