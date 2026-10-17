'use client';

import type { RefObject } from 'react';
import { Code2 } from 'lucide-react';
import { FileIcon } from './FileIcon';

export interface LineRange {
  start: number;
  end: number;
}

/** Center column of the Code page: file tab bar plus line-numbered source with highlighting. */
export function CodeViewer({
  selectedFilePath,
  fileVersion,
  content,
  highlightLines,
  highlightRef,
  onClearHighlight,
  isStreaming,
  hasFiles,
}: {
  selectedFilePath: string | null;
  /** Version of the selected file, if it is in the current file list. */
  fileVersion: number | undefined;
  content: string;
  highlightLines: LineRange | null;
  /** Attached to the first highlighted line so the page can scroll it into view. */
  highlightRef: RefObject<HTMLDivElement | null>;
  onClearHighlight: () => void;
  isStreaming: boolean;
  hasFiles: boolean;
}) {
  const codeLines = content.split('\n');

  return (
    <div className="flex-1 flex flex-col bg-[#1e1e2e] min-w-0">
      {/* File tab bar */}
      <div className="px-3 py-1.5 border-b border-[#313244] flex items-center gap-2 bg-[#181825]">
        {selectedFilePath ? (
          <>
            <FileIcon path={selectedFilePath} />
            <span className="text-xs text-[#cdd6f4] font-mono">{selectedFilePath}</span>
            {fileVersion !== undefined && (
              <span className="text-[10px] text-[#6c7086]">v{fileVersion}</span>
            )}
          </>
        ) : (
          <span className="text-xs text-[#6c7086]">No file selected</span>
        )}
      </div>

      {/* Code content */}
      <div className="flex-1 overflow-auto">
        {content ? (
          <div className="font-mono text-sm">
            {codeLines.map((line, i) => {
              const lineNum = i + 1;
              const isHighlighted =
                highlightLines && lineNum >= highlightLines.start && lineNum <= highlightLines.end;
              const isFirstHighlight = isHighlighted && lineNum === highlightLines!.start;
              return (
                <div
                  key={i}
                  ref={isFirstHighlight ? highlightRef : undefined}
                  className={`flex ${
                    isHighlighted
                      ? 'bg-[#f59e0b]/15 border-l-2 border-[#f59e0b]'
                      : 'hover:bg-[#313244]/50'
                  }`}
                  onClick={() => {
                    if (isHighlighted) onClearHighlight();
                  }}
                >
                  <span
                    className={`w-12 text-right pr-4 select-none shrink-0 py-px ${
                      isHighlighted ? 'text-[#f59e0b] font-medium' : 'text-[#6c7086]'
                    }`}
                  >
                    {lineNum}
                  </span>
                  <span className="text-[#cdd6f4] py-px whitespace-pre">{line}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-[#6c7086]">
            <div className="text-center">
              <Code2 size={32} className="mx-auto mb-2 opacity-40" />
              <p className="text-sm">
                {isStreaming
                  ? 'Agent is generating code...'
                  : hasFiles
                    ? 'Select a file from the tree'
                    : 'No code generated yet'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
