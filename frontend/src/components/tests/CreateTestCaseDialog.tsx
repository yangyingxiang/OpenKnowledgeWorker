'use client';

import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import type { TestCase } from '@/lib/api';

const INPUT_CLASS =
  'w-full px-3 py-2 rounded-lg border border-[var(--okw-border)] text-sm focus:outline-none focus:border-[var(--okw-primary)]';
const TEXTAREA_CLASS =
  'w-full px-3 py-2 rounded-lg border border-[var(--okw-border)] text-sm font-mono focus:outline-none focus:border-[var(--okw-primary)] resize-none';

/**
 * Modal form for creating a test case. Input data / assertions are entered as JSON and
 * validated before `onSubmit` is called. The form is cleared after a successful submit.
 */
export function CreateTestCaseDialog({
  open,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: Partial<TestCase>) => Promise<void>;
}) {
  const [newTestName, setNewTestName] = useState('');
  const [newTestDesc, setNewTestDesc] = useState('');
  const [newInputData, setNewInputData] = useState('{}');
  const [newAssertions, setNewAssertions] = useState('{}');

  const handleCreate = async () => {
    try {
      let inputData: Record<string, unknown>;
      let assertions: Record<string, unknown>;
      try {
        inputData = JSON.parse(newInputData);
      } catch {
        return alert('Invalid JSON in input data');
      }
      try {
        assertions = JSON.parse(newAssertions);
      } catch {
        return alert('Invalid JSON in assertions');
      }

      await onSubmit({
        test_name: newTestName,
        description: newTestDesc || undefined,
        input_data: inputData,
        expected_assertions: assertions,
      });
      onOpenChange(false);
      setNewTestName('');
      setNewTestDesc('');
      setNewInputData('{}');
      setNewAssertions('{}');
    } catch (err) {
      console.error('Failed to create test case:', err);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40 animate-[fadeSlideIn_0.15s_ease-out_both]" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl p-6 w-full max-w-lg z-50 max-h-[90vh] overflow-y-auto animate-[fadeSlideIn_0.2s_ease-out_both]">
          <Dialog.Title className="text-lg font-semibold text-[var(--okw-text)] mb-4">
            Create Test Case
          </Dialog.Title>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--okw-text)] mb-1">
                Test Name *
              </label>
              <input
                value={newTestName}
                onChange={(e) => setNewTestName(e.target.value)}
                placeholder="e.g., chen_baseline"
                className={INPUT_CLASS}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--okw-text)] mb-1">
                Description
              </label>
              <input
                value={newTestDesc}
                onChange={(e) => setNewTestDesc(e.target.value)}
                placeholder="Brief description..."
                className={INPUT_CLASS}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--okw-text)] mb-1">
                Input Data (JSON) *
              </label>
              <textarea
                value={newInputData}
                onChange={(e) => setNewInputData(e.target.value)}
                rows={6}
                className={TEXTAREA_CLASS}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--okw-text)] mb-1">
                Expected Assertions (JSON)
              </label>
              <textarea
                value={newAssertions}
                onChange={(e) => setNewAssertions(e.target.value)}
                rows={4}
                className={TEXTAREA_CLASS}
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <Dialog.Close asChild>
              <button className="px-4 py-2 rounded-lg text-sm text-[var(--okw-text-muted)] hover:bg-[var(--okw-bg)]">
                Cancel
              </button>
            </Dialog.Close>
            <button
              onClick={handleCreate}
              disabled={!newTestName.trim()}
              className="px-4 py-2 rounded-lg bg-[var(--okw-primary)] text-white text-sm font-medium hover:bg-[var(--okw-primary-dark)] disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
