const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5003';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(error.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

function upload(path: string, formData: FormData) {
  return fetch(`${API_URL}${path}`, {
    method: 'POST',
    body: formData,
  }).then(async (res) => {
    if (!res.ok) {
      const error = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(error.error || `Upload failed: ${res.status}`);
    }
    return res.json();
  });
}

function sseStream(path: string, body?: object) {
  return fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
}

// Process API
export const api = {
  // Processes
  listProcesses: () => request<Process[]>('/api/processes'),
  createProcess: (data: Partial<Process>) =>
    request<Process>('/api/processes', { method: 'POST', body: JSON.stringify(data) }),
  getProcess: (id: string) => request<Process>(`/api/processes/${id}`),
  updateProcess: (id: string, data: Partial<Process>) =>
    request<Process>(`/api/processes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProcess: (id: string) =>
    request<{ success: boolean }>(`/api/processes/${id}`, { method: 'DELETE' }),

  // Documents
  listDocuments: (processId: string) =>
    request<Document[]>(`/api/processes/${processId}/documents`),
  uploadDocument: (processId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return upload(`/api/processes/${processId}/documents`, formData);
  },
  getDocument: (processId: string, docId: string) =>
    request<Document>(`/api/processes/${processId}/documents/${docId}`),
  deleteDocument: (processId: string, docId: string) =>
    request<{ success: boolean }>(`/api/processes/${processId}/documents/${docId}`, {
      method: 'DELETE',
    }),

  // PDD
  getCurrentPdd: (processId: string) => request<PddVersion>(`/api/processes/${processId}/pdd`),
  listPddVersions: (processId: string) =>
    request<PddVersionSummary[]>(`/api/processes/${processId}/pdd/versions`),
  getPddVersion: (processId: string, versionId: string) =>
    request<PddVersion>(`/api/processes/${processId}/pdd/versions/${versionId}`),
  updatePdd: (processId: string, data: { content: string; change_summary?: string }) =>
    request<PddVersion>(`/api/processes/${processId}/pdd`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  researchPdd: (processId: string) => sseStream(`/api/processes/${processId}/pdd/research`),
  getPddProvenance: (processId: string) =>
    request<ProvenanceItem[]>(`/api/processes/${processId}/pdd/provenance`),

  // Chat
  listChatSessions: (processId: string) =>
    request<ChatSession[]>(`/api/processes/${processId}/chat/sessions`),
  createChatSession: (processId: string, data?: { expert_name?: string; expert_role?: string }) =>
    request<ChatSession>(`/api/processes/${processId}/chat/sessions`, {
      method: 'POST',
      body: JSON.stringify(data || {}),
    }),
  getChatSession: (processId: string, sessionId: string) =>
    request<ChatSession>(`/api/processes/${processId}/chat/sessions/${sessionId}`),
  updateChatSession: (processId: string, sessionId: string, data: Partial<ChatSession>) =>
    request<ChatSession>(`/api/processes/${processId}/chat/sessions/${sessionId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  sendMessage: (
    processId: string,
    sessionId: string,
    content: string,
    context?: 'sop' | 'code' | 'tests',
  ) =>
    sseStream(`/api/processes/${processId}/chat/sessions/${sessionId}/message`, {
      content,
      context,
    }),

  // Knowledge
  listKnowledge: (processId: string) =>
    request<KnowledgeItem[]>(`/api/processes/${processId}/knowledge`),
  addKnowledge: (processId: string, data: Partial<KnowledgeItem>) =>
    request<KnowledgeItem>(`/api/processes/${processId}/knowledge`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deleteKnowledge: (processId: string, itemId: string) =>
    request<{ success: boolean }>(`/api/processes/${processId}/knowledge/${itemId}`, {
      method: 'DELETE',
    }),

  // Questions
  listQuestions: (processId: string, status?: string) =>
    request<Question[]>(
      `/api/processes/${processId}/questions${status ? `?status=${status}` : ''}`,
    ),
  createQuestion: (processId: string, data: Partial<Question>) =>
    request<Question>(`/api/processes/${processId}/questions`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateQuestion: (processId: string, qId: string, data: Partial<Question>) =>
    request<Question>(`/api/processes/${processId}/questions/${qId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteQuestion: (processId: string, qId: string) =>
    request<{ success: boolean }>(`/api/processes/${processId}/questions/${qId}`, {
      method: 'DELETE',
    }),
  resetAllQuestions: (processId: string) =>
    request<{
      success: boolean;
      questions_reset: number;
      knowledge_deleted: number;
      pdd_reverted: boolean;
    }>(`/api/processes/${processId}/questions/reset-all`, { method: 'POST' }),

  // Multi-file Coding Agent
  startCodingAgent: (processId: string, maxIterations?: number) =>
    sseStream(`/api/processes/${processId}/coding/start`, { max_iterations: maxIterations ?? 10 }),
  listCodingProjects: (processId: string) =>
    request<CodeProject[]>(`/api/processes/${processId}/coding/projects`),
  getCodingProject: (processId: string, projectId: string) =>
    request<CodeProjectWithFiles>(`/api/processes/${processId}/coding/projects/${projectId}`),
  getProjectFiles: (processId: string, projectId: string) =>
    request<CodeFileSummary[]>(`/api/processes/${processId}/coding/projects/${projectId}/files`),
  getProjectFile: (processId: string, projectId: string, fileId: string) =>
    request<CodeFile>(`/api/processes/${processId}/coding/projects/${projectId}/files/${fileId}`),
  retryCodingAgent: (processId: string, projectId: string) =>
    sseStream(`/api/processes/${processId}/coding/projects/${projectId}/retry`),
  downloadProject: (processId: string, projectId: string) =>
    `${API_URL}/api/processes/${processId}/coding/projects/${projectId}/download`,

  // Tests
  listTestCases: (processId: string) =>
    request<TestCase[]>(`/api/processes/${processId}/tests/cases`),
  createTestCase: (processId: string, data: Partial<TestCase>) =>
    request<TestCase>(`/api/processes/${processId}/tests/cases`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateTestCase: (processId: string, tcId: string, data: Partial<TestCase>) =>
    request<TestCase>(`/api/processes/${processId}/tests/cases/${tcId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteTestCase: (processId: string, tcId: string) =>
    request<{ success: boolean }>(`/api/processes/${processId}/tests/cases/${tcId}`, {
      method: 'DELETE',
    }),
  runTests: (processId: string, data: { mode: string; test_case_ids?: string[] }) =>
    sseStream(`/api/processes/${processId}/tests/run`, data),
  listTestRuns: (processId: string) => request<TestRun[]>(`/api/processes/${processId}/tests/runs`),
  bulkUploadTests: (processId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return upload(`/api/processes/${processId}/tests/cases/bulk`, formData);
  },

  // Domain packs (bundled example processes)
  listDomainPacks: () => request<DomainPack[]>('/api/domain-packs'),
  installDomainPack: (packId: string, withSampleOutputs = true) =>
    request<Process>(`/api/domain-packs/${packId}/install`, {
      method: 'POST',
      body: JSON.stringify({ with_sample_outputs: withSampleOutputs }),
    }),

  // Background jobs: re-attach to a job's event stream after a disconnect
  resumeJobEvents: (jobId: string, after: number) =>
    fetch(`${API_URL}/api/jobs/${jobId}/events?after=${after}`, {
      headers: { Accept: 'text/event-stream' },
    }),
};

export interface DomainPack {
  id: string;
  name: string;
  domain: string;
  description: string;
}

// Types
export interface Process {
  id: string;
  name: string;
  domain: string | null;
  description: string | null;
  status: string;
  key_inputs: string[];
  key_outputs: string[];
  metadata: Record<string, unknown>;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  process_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  page_count: number | null;
  status: string;
  has_extracted_text: boolean;
  extracted_text?: string;
  created_at: string;
}

export interface PddVersion {
  id: string;
  process_id: string;
  version_number: number;
  content: string;
  change_summary: string | null;
  change_source: string | null;
  parent_version_id: string | null;
  created_at: string;
}

export interface PddVersionSummary {
  id: string;
  version_number: number;
  change_summary: string | null;
  change_source: string | null;
  created_at: string;
}

export interface ChatSession {
  id: string;
  process_id: string;
  expert_name: string;
  expert_role: string;
  status: string;
  message_count: number;
  messages?: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tool_calls?: { name: string; input: Record<string, unknown> }[];
  tool_results?: { name: string; result: string }[];
  created_at: string;
}

export interface KnowledgeItem {
  id: string;
  process_id: string;
  section: string;
  content: string;
  confidence: 'CONFIRMED' | 'TENTATIVE';
  source_type: string;
  source_id: string | null;
  source_detail: string | null;
  created_at: string;
}

export interface Question {
  id: string;
  process_id: string;
  display_id: string;
  text: string;
  target_roles: string[];
  priority: number;
  status: 'OPEN' | 'ANSWERED' | 'DISMISSED';
  related_pdd_section: string | null;
  answer: string | null;
  created_at: string;
}

export interface ProvenanceItem {
  id: string;
  sentence_hash: string;
  sentence_text: string;
  section_path: string;
  source_type: string;
  source_id: string | null;
  source_detail: string | null;
  actor: string | null;
}

export interface TestCase {
  id: string;
  process_id: string;
  test_name: string;
  description: string | null;
  input_data: Record<string, unknown>;
  expected_assertions: Record<string, unknown>;
  mock_llm_judge: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
}

export interface TestRun {
  id: string;
  process_id: string;
  test_case_id: string | null;
  mode: string;
  status: string;
  llm_result: Record<string, unknown> | null;
  code_result: Record<string, unknown> | null;
  assertions_passed: number | null;
  assertions_total: number | null;
  duration_ms: number | null;
  created_at: string;
}

// Multi-file Coding Agent types
export interface CodeProject {
  id: string;
  process_id: string;
  pdd_version_id: string;
  status: 'planning' | 'coding' | 'testing' | 'fixing' | 'complete' | 'error';
  iteration: number;
  max_iterations: number;
  test_summary: { passed: number; failed: number; errors: number; output: string } | null;
  agent_log: { phase: string; detail?: string; error?: string; timestamp?: string }[];
  sandbox_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface CodeProjectWithFiles extends CodeProject {
  files: CodeFile[];
}

export interface CodeFile {
  id: string;
  project_id: string;
  file_path: string;
  content: string;
  file_type: 'source' | 'test' | 'config' | 'init';
  version: number;
  pdd_section_ref: string | null;
  created_at: string;
  updated_at: string;
}

export interface CodeFileSummary {
  id: string;
  file_path: string;
  file_type: string;
  version: number;
  lines: number;
}
