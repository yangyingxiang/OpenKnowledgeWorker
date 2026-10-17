import type { CodeFileSummary } from '@/lib/api';

/** A node in the project file tree shown on the Code page. */
export interface TreeNode {
  name: string;
  /** Full path from the project root, e.g. "engine/steps/income.py". */
  path: string;
  isDir: boolean;
  children: TreeNode[];
  file?: CodeFileSummary;
}

/** Build a nested tree from a flat list of files. Directories sort first, then alphabetical. */
export function buildTree(files: CodeFileSummary[]): TreeNode[] {
  const root: TreeNode[] = [];
  for (const f of files) {
    const parts = f.file_path.split('/');
    let level = root;
    let currentPath = '';
    for (let i = 0; i < parts.length; i++) {
      currentPath += (i > 0 ? '/' : '') + parts[i];
      const isLast = i === parts.length - 1;
      let existing = level.find((n) => n.name === parts[i]);
      if (!existing) {
        existing = {
          name: parts[i],
          path: currentPath,
          isDir: !isLast,
          children: [],
          file: isLast ? f : undefined,
        };
        level.push(existing);
      }
      level = existing.children;
    }
  }
  // Sort: dirs first, then alphabetical
  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach((n) => sortNodes(n.children));
  };
  sortNodes(root);
  return root;
}

/** All ancestor directory paths of a file, e.g. "a/b/c.py" → ["a", "a/b"]. */
export function parentDirs(filePath: string): string[] {
  const parts = filePath.split('/');
  const dirs: string[] = [];
  for (let i = 1; i < parts.length; i++) {
    dirs.push(parts.slice(0, i).join('/'));
  }
  return dirs;
}
