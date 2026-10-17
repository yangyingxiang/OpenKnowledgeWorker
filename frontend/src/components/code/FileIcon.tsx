import { Braces, FileCode, FileText, TestTube2 } from 'lucide-react';

/** Icon for a file in the code explorer, chosen from its path. */
export function FileIcon({ path }: { path: string }) {
  if (path.endsWith('.py')) return <FileCode size={14} className="text-[#3572A5]" />;
  if (path.includes('test')) return <TestTube2 size={14} className="text-[#22c55e]" />;
  if (path === '__init__.py') return <Braces size={14} className="text-[#6c7086]" />;
  return <FileText size={14} className="text-[#cdd6f4]" />;
}
