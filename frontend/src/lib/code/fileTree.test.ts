import { describe, expect, it } from 'vitest';
import type { CodeFileSummary } from '@/lib/api';
import { buildTree, parentDirs, type TreeNode } from './fileTree';

const file = (file_path: string): CodeFileSummary => ({
  id: file_path,
  file_path,
  file_type: 'source',
  version: 1,
  lines: 10,
});

/** Compact representation: dirs end with "/", children nested. */
function shape(nodes: TreeNode[]): unknown[] {
  return nodes.map((n) => (n.isDir ? { [n.name + '/']: shape(n.children) } : n.name));
}

describe('buildTree', () => {
  it('nests files under directories, sorting directories first then by name', () => {
    const tree = buildTree([
      file('setup.py'),
      file('engine/steps/b.py'),
      file('engine/main.py'),
      file('engine/steps/a.py'),
      file('README.md'),
    ]);
    expect(shape(tree)).toEqual([
      { 'engine/': [{ 'steps/': ['a.py', 'b.py'] }, 'main.py'] },
      'README.md',
      'setup.py',
    ]);
  });

  it('records full paths and attaches the file summary to leaves', () => {
    const [engine] = buildTree([file('engine/main.py')]);
    expect(engine.path).toBe('engine');
    expect(engine.file).toBeUndefined();
    expect(engine.children[0].path).toBe('engine/main.py');
    expect(engine.children[0].file?.id).toBe('engine/main.py');
  });
});

describe('parentDirs', () => {
  it('lists every ancestor directory', () => {
    expect(parentDirs('a/b/c.py')).toEqual(['a', 'a/b']);
    expect(parentDirs('top.py')).toEqual([]);
  });
});
