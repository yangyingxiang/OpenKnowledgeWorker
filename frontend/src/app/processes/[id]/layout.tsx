'use client';

import { useState, useEffect, use } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { api, Process } from '@/lib/api';
import { Logo } from '@/components/shared/Logo';
import { ArrowLeft, FileText, BookOpen, Code2, TestTube } from 'lucide-react';

const NAV_ITEMS = [
  { key: 'documents', label: 'Documents', icon: FileText, href: 'documents' },
  { key: 'pdd', label: 'SOP Studio', icon: BookOpen, href: 'pdd' },
  { key: 'code', label: 'Code Agent', icon: Code2, href: 'code' },
  { key: 'tests', label: 'Test Suite', icon: TestTube, href: 'tests' },
];

export default function ProcessLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const pathname = usePathname();
  const [process, setProcess] = useState<Process | null>(null);

  useEffect(() => {
    api.getProcess(id).then(setProcess).catch(console.error);
  }, [id]);

  const activeTab = NAV_ITEMS.find((item) => pathname.includes(`/${item.key}`))?.key || 'documents';

  return (
    <div className="h-screen bg-[var(--okw-bg)] flex flex-col overflow-hidden">
      {/* Top bar */}
      <header className="border-b border-[var(--okw-border)] bg-white shrink-0">
        <div className="px-6 py-3 flex items-center gap-4">
          <button
            onClick={() => router.push('/processes')}
            className="p-1.5 rounded-lg hover:bg-[var(--okw-bg)] transition-colors"
          >
            <ArrowLeft size={18} className="text-[var(--okw-text-muted)]" />
          </button>
          <div className="flex items-center gap-3">
            <Logo size={28} />
            <div>
              <h1 className="text-sm font-semibold text-[var(--okw-text)]">
                {process?.name || 'Loading...'}
              </h1>
              {process?.domain && (
                <p className="text-xs text-[var(--okw-text-muted)]">{process.domain}</p>
              )}
            </div>
          </div>
          {process && (
            <span
              className={`ml-2 px-2 py-0.5 rounded-full text-xs font-medium ${
                process.status === 'active'
                  ? 'bg-green-50 text-green-700'
                  : 'bg-yellow-50 text-yellow-700'
              }`}
            >
              {process.status}
            </span>
          )}
        </div>
        {/* Tab navigation */}
        <nav className="px-6 flex gap-0">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.key;
            return (
              <button
                key={item.key}
                onClick={() => router.push(`/processes/${id}/${item.href}`)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  isActive
                    ? 'border-[var(--okw-primary)] text-[var(--okw-primary)]'
                    : 'border-transparent text-[var(--okw-text-muted)] hover:text-[var(--okw-text)] hover:border-[var(--okw-border)]'
                }`}
              >
                <Icon size={16} />
                {item.label}
              </button>
            );
          })}
        </nav>
      </header>

      {/* Page content */}
      <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
    </div>
  );
}
