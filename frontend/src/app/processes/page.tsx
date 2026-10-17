'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api, Process } from '@/lib/api';
import { Logo } from '@/components/shared/Logo';
import { ExamplePacks } from '@/components/processes/ExamplePacks';
import { Plus, FolderOpen, MoreVertical, Trash2, Clock, FileText, ArrowRight } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import * as AlertDialog from '@radix-ui/react-alert-dialog';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

export default function ProcessesPage() {
  const router = useRouter();
  const [processes, setProcesses] = useState<Process[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDomain, setNewDomain] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<Process | null>(null);

  const loadProcesses = useCallback(async () => {
    try {
      const data = await api.listProcesses();
      setProcesses(data);
    } catch (err) {
      console.error('Failed to load processes:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProcesses();
  }, [loadProcesses]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const p = await api.createProcess({
        name: newName.trim(),
        domain: newDomain.trim() || undefined,
        description: newDescription.trim() || undefined,
      });
      setShowCreate(false);
      setNewName('');
      setNewDomain('');
      setNewDescription('');
      router.push(`/processes/${p.id}/documents`);
    } catch (err) {
      console.error('Failed to create:', err);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteProcess(deleteTarget.id);
      setDeleteTarget(null);
      loadProcesses();
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--okw-bg)]">
      {/* Header */}
      <header className="border-b border-[var(--okw-border)] bg-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Logo size={32} />
            <h1 className="text-xl font-semibold text-[var(--okw-text)]">OpenKnowledgeWorker</h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--okw-primary-light)] text-[var(--okw-primary)] font-medium">
              Process Automation
            </span>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--okw-primary)] text-white font-medium text-sm hover:bg-[var(--okw-primary-dark)] transition-colors"
          >
            <Plus size={16} />
            New Process
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-[var(--okw-text)]">Your Processes</h2>
          <p className="text-[var(--okw-text-muted)] mt-1">
            Manage and automate business process documentation
          </p>
        </div>

        <ExamplePacks onInstalled={(p) => router.push(`/processes/${p.id}/pdd`)} />

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-[var(--okw-primary)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : processes.length === 0 ? (
          <div className="text-center py-20 animate-fade-in">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[var(--okw-primary-light)] flex items-center justify-center">
              <FolderOpen size={28} className="text-[var(--okw-primary)]" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--okw-text)]">No processes yet</h3>
            <p className="text-[var(--okw-text-muted)] mt-1 mb-6">
              Create your first process to get started
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="px-5 py-2.5 rounded-lg bg-[var(--okw-primary)] text-white font-medium text-sm hover:bg-[var(--okw-primary-dark)] transition-colors"
            >
              Create Process
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {processes.map((p, i) => (
              <div
                key={p.id}
                className="group bg-white rounded-xl border border-[var(--okw-border)] p-5 hover:shadow-lg hover:border-[var(--okw-primary)]/20 transition-all cursor-pointer animate-fade-in-up"
                style={{ animationDelay: `${i * 60}ms` }}
                onClick={() => router.push(`/processes/${p.id}/documents`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="font-semibold text-[var(--okw-text)] group-hover:text-[var(--okw-primary)] transition-colors">
                      {p.name}
                    </h3>
                    {p.domain && (
                      <span className="text-xs text-[var(--okw-text-muted)] bg-[var(--okw-bg)] px-2 py-0.5 rounded mt-1 inline-block">
                        {p.domain}
                      </span>
                    )}
                  </div>
                  <DropdownMenu.Root>
                    <DropdownMenu.Trigger asChild>
                      <button
                        onClick={(e) => e.stopPropagation()}
                        className="p-1 rounded hover:bg-[var(--okw-bg)] opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <MoreVertical size={16} className="text-[var(--okw-text-muted)]" />
                      </button>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Portal>
                      <DropdownMenu.Content
                        className="bg-white rounded-lg shadow-lg border border-[var(--okw-border)] py-1 min-w-[140px] z-50"
                        sideOffset={5}
                      >
                        <DropdownMenu.Item
                          className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 cursor-pointer outline-none"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteTarget(p);
                          }}
                        >
                          <Trash2 size={14} /> Delete
                        </DropdownMenu.Item>
                      </DropdownMenu.Content>
                    </DropdownMenu.Portal>
                  </DropdownMenu.Root>
                </div>
                {p.description && (
                  <p className="text-sm text-[var(--okw-text-muted)] mb-3 line-clamp-2">
                    {p.description}
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-[var(--okw-text-muted)]">
                  <span className="flex items-center gap-1">
                    <FileText size={12} /> {p.document_count} docs
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {new Date(p.updated_at).toLocaleDateString()}
                  </span>
                  <span
                    className={`ml-auto px-2 py-0.5 rounded-full text-xs font-medium ${
                      p.status === 'active'
                        ? 'bg-green-50 text-green-700'
                        : p.status === 'draft'
                          ? 'bg-yellow-50 text-yellow-700'
                          : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {p.status}
                  </span>
                </div>
                <div className="mt-3 pt-3 border-t border-[var(--okw-border)] flex items-center justify-end">
                  <span className="text-xs text-[var(--okw-primary)] font-medium flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    Open <ArrowRight size={12} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create Dialog */}
      <Dialog.Root open={showCreate} onOpenChange={setShowCreate}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/40 animate-fade-in z-40" />
          <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md animate-fade-in-up z-50">
            <Dialog.Title className="text-lg font-semibold text-[var(--okw-text)] mb-4">
              Create New Process
            </Dialog.Title>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[var(--okw-text)] mb-1">
                  Process Name *
                </label>
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g., Income Verification"
                  className="w-full px-3 py-2 rounded-lg border border-[var(--okw-border)] text-sm focus:outline-none focus:border-[var(--okw-primary)] focus:ring-1 focus:ring-[var(--okw-primary)]"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--okw-text)] mb-1">
                  Domain
                </label>
                <input
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  placeholder="e.g., Mortgage Underwriting"
                  className="w-full px-3 py-2 rounded-lg border border-[var(--okw-border)] text-sm focus:outline-none focus:border-[var(--okw-primary)] focus:ring-1 focus:ring-[var(--okw-primary)]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--okw-text)] mb-1">
                  Description
                </label>
                <textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Brief description of the process..."
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg border border-[var(--okw-border)] text-sm focus:outline-none focus:border-[var(--okw-primary)] focus:ring-1 focus:ring-[var(--okw-primary)] resize-none"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Dialog.Close asChild>
                <button className="px-4 py-2 rounded-lg text-sm text-[var(--okw-text-muted)] hover:bg-[var(--okw-bg)] transition-colors">
                  Cancel
                </button>
              </Dialog.Close>
              <button
                onClick={handleCreate}
                disabled={!newName.trim()}
                className="px-4 py-2 rounded-lg bg-[var(--okw-primary)] text-white text-sm font-medium hover:bg-[var(--okw-primary-dark)] transition-colors disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Delete Confirmation */}
      <AlertDialog.Root open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialog.Portal>
          <AlertDialog.Overlay className="fixed inset-0 bg-black/40 animate-fade-in z-40" />
          <AlertDialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm animate-fade-in-up z-50">
            <AlertDialog.Title className="text-lg font-semibold text-[var(--okw-text)]">
              Delete Process?
            </AlertDialog.Title>
            <AlertDialog.Description className="text-sm text-[var(--okw-text-muted)] mt-2">
              This will archive &ldquo;{deleteTarget?.name}&rdquo; and all its data. This action
              cannot be easily undone.
            </AlertDialog.Description>
            <div className="flex justify-end gap-3 mt-6">
              <AlertDialog.Cancel asChild>
                <button className="px-4 py-2 rounded-lg text-sm text-[var(--okw-text-muted)] hover:bg-[var(--okw-bg)]">
                  Cancel
                </button>
              </AlertDialog.Cancel>
              <AlertDialog.Action asChild>
                <button
                  onClick={handleDelete}
                  className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
                >
                  Delete
                </button>
              </AlertDialog.Action>
            </div>
          </AlertDialog.Content>
        </AlertDialog.Portal>
      </AlertDialog.Root>
    </div>
  );
}
