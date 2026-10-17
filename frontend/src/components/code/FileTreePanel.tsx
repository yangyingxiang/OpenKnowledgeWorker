'use client';

import { ChevronDown, ChevronRight, FolderTree, Loader2 } from 'lucide-react';
import type { TreeNode } from '@/lib/code/fileTree';
import { FileIcon } from './FileIcon';

/** Left column of the Code page: the generated project's file tree. */
export function FileTreePanel({
  fileTree,
  fileCount,
  selectedPath,
  onSelect,
  expandedDirs,
  toggleDir,
  isStreaming,
  filesWritten,
}: {
  fileTree: TreeNode[];
  fileCount: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  expandedDirs: Set<string>;
  toggleDir: (path: string) => void;
  isStreaming: boolean;
  /** Files reported by the agent while it is still writing (shown before the tree loads). */
  filesWritten: string[];
}) {
  return (
    <div className="w-56 shrink-0 bg-[#1e1e2e] border-r border-[#313244] flex flex-col">
      <div className="px-3 py-2 border-b border-[#313244] flex items-center gap-1.5">
        <FolderTree size={13} className="text-[#f59e0b]" />
        <span className="text-xs font-medium text-[#cdd6f4]">Project Files</span>
        <span className="ml-auto text-[10px] text-[#6c7086]">{fileCount}</span>
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {fileTree.length > 0 ? (
          fileTree.map((node) => (
            <TreeNodeView
              key={node.path}
              node={node}
              depth={0}
              selectedPath={selectedPath}
              onSelect={onSelect}
              expandedDirs={expandedDirs}
              toggleDir={toggleDir}
            />
          ))
        ) : (
          <div className="px-3 py-8 text-center text-[#6c7086] text-xs">
            {isStreaming ? (
              <>
                <Loader2 size={16} className="mx-auto mb-2 animate-spin" />
                Agent is generating files...
              </>
            ) : (
              <>No files yet. Ask the chat to generate code.</>
            )}
          </div>
        )}

        {/* Show files being written during stream */}
        {isStreaming && filesWritten.length > 0 && fileCount === 0 && (
          <div className="px-3 py-2 border-t border-[#313244]">
            <span className="text-[10px] text-[#6c7086] uppercase tracking-wider">Writing...</span>
            {filesWritten.map((f) => (
              <div key={f} className="text-xs text-[#a6adc8] py-0.5 flex items-center gap-1">
                <FileIcon path={f} /> {f}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TreeNodeView({
  node,
  depth,
  selectedPath,
  onSelect,
  expandedDirs,
  toggleDir,
}: {
  node: TreeNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  expandedDirs: Set<string>;
  toggleDir: (path: string) => void;
}) {
  const isExpanded = expandedDirs.has(node.path);
  const isSelected = selectedPath === node.path;

  if (node.isDir) {
    return (
      <>
        <button
          onClick={() => toggleDir(node.path)}
          className="w-full flex items-center gap-1 px-2 py-1 text-xs hover:bg-[#313244] transition-colors"
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {isExpanded ? (
            <ChevronDown size={12} className="text-[#6c7086] shrink-0" />
          ) : (
            <ChevronRight size={12} className="text-[#6c7086] shrink-0" />
          )}
          <FolderTree size={13} className="text-[#f59e0b] shrink-0" />
          <span className="text-[#cdd6f4] truncate">{node.name}</span>
        </button>
        {isExpanded &&
          node.children.map((child) => (
            <TreeNodeView
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              expandedDirs={expandedDirs}
              toggleDir={toggleDir}
            />
          ))}
      </>
    );
  }

  return (
    <button
      onClick={() => onSelect(node.path)}
      className={`w-full flex items-center gap-1.5 px-2 py-1 text-xs transition-colors ${
        isSelected ? 'bg-[#45475a] text-white' : 'text-[#cdd6f4] hover:bg-[#313244]'
      }`}
      style={{ paddingLeft: `${depth * 12 + 20}px` }}
    >
      <FileIcon path={node.name} />
      <span className="truncate">{node.name}</span>
      {node.file && (
        <span className="ml-auto text-[10px] text-[#6c7086] shrink-0">v{node.file.version}</span>
      )}
    </button>
  );
}
