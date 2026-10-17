'use client';

import { useMemo } from 'react';
import { parseText, groupBlocks } from '@/lib/documents/parseText';

/*
 * Professional Document Renderer
 * Converts extracted plain text into a styled, print-quality HTML view
 * (a single "page" with a header, typed body blocks and a footer).
 */

interface DocumentRendererProps {
  text: string;
  filename: string;
  documentId?: string;
}

export function DocumentRenderer({ text, filename, documentId }: DocumentRendererProps) {
  const parsed = useMemo(() => parseText(text), [text]);

  // Group consecutive table rows together, consecutive key-value pairs together
  const blocks = useMemo(() => groupBlocks(parsed), [parsed]);

  return (
    <div className="flex justify-center py-8 px-4">
      <div
        style={{
          width: '100%',
          maxWidth: '816px' /* ~8.5 inches at 96dpi */,
          background: '#fff',
          boxShadow: '0 1px 3px rgba(0,0,0,0.08), 0 8px 30px rgba(0,0,0,0.07)',
          borderRadius: '4px',
          position: 'relative',
          fontFamily: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
          color: '#1a1a1a',
          fontSize: '13px',
          lineHeight: '1.6',
        }}
      >
        {/* Document header */}
        <div
          style={{
            padding: '24px 40px 16px',
            borderBottom: '2px solid #1a3a5c',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
          }}
        >
          <div>
            <div
              style={{
                fontSize: '18px',
                fontWeight: 700,
                color: '#1a3a5c',
                letterSpacing: '0.3px',
              }}
            >
              {filename.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ')}
            </div>
            <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>{filename}</div>
          </div>
          <div
            style={{
              fontSize: '9px',
              fontWeight: 600,
              letterSpacing: '1.5px',
              textTransform: 'uppercase',
              color: '#94a3b8',
              border: '1px solid #e2e8f0',
              borderRadius: '3px',
              padding: '2px 8px',
            }}
          >
            Extracted Document
          </div>
        </div>

        {/* Document body */}
        <div style={{ padding: '24px 40px 32px' }}>
          {blocks.map((block, bi) => {
            // --- Section header ---
            if (block.type === 'section-header') {
              return block.items.map((item, ii) => (
                <div
                  key={`${bi}-${ii}`}
                  style={{
                    fontSize: '13px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.8px',
                    color: '#1a3a5c',
                    marginTop: bi === 0 && ii === 0 ? '0' : '20px',
                    marginBottom: '8px',
                    paddingBottom: '4px',
                    borderBottom: '1px solid #e5e7eb',
                    background: '#f8fafc',
                    padding: '6px 10px',
                    borderRadius: '2px',
                  }}
                >
                  {item.raw.trim()}
                </div>
              ));
            }

            // --- Key-value group ---
            if (block.type === 'kv-group') {
              return (
                <div
                  key={bi}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'minmax(140px, auto) 1fr',
                    gap: '0',
                    margin: '8px 0 12px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '4px',
                    overflow: 'hidden',
                  }}
                >
                  {block.items.map((item, ii) => (
                    <div key={ii} style={{ display: 'contents' }}>
                      <div
                        style={{
                          padding: '6px 12px',
                          fontWeight: 600,
                          fontSize: '12px',
                          color: '#374151',
                          background: '#f9fafb',
                          borderBottom: ii < block.items.length - 1 ? '1px solid #f0f0f0' : 'none',
                          borderRight: '1px solid #e5e7eb',
                        }}
                      >
                        {item.key}
                      </div>
                      <div
                        style={{
                          padding: '6px 12px',
                          fontSize: '12px',
                          color: '#1a1a1a',
                          borderBottom: ii < block.items.length - 1 ? '1px solid #f0f0f0' : 'none',
                        }}
                      >
                        {item.value}
                      </div>
                    </div>
                  ))}
                </div>
              );
            }

            // --- Table ---
            if (block.type === 'table') {
              // Filter out separator rows, keep data rows
              const dataRows = block.items.filter((i) => i.type === 'table-row' && i.cells);
              if (dataRows.length === 0) return null;

              const isFirstRowHeader =
                dataRows.length > 1 &&
                block.items.length > 1 &&
                (block.items[1]?.type === 'table-separator' ||
                  (dataRows[0]?.cells?.every((c) => /^[A-Z]/.test(c)) ?? false));

              return (
                <div key={bi} style={{ margin: '8px 0 12px', overflowX: 'auto' }}>
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: '12px',
                      border: '1px solid #d1d5db',
                      borderRadius: '4px',
                    }}
                  >
                    {isFirstRowHeader && (
                      <thead>
                        <tr>
                          {dataRows[0].cells!.map((cell, ci) => (
                            <th
                              key={ci}
                              style={{
                                padding: '7px 12px',
                                textAlign: 'left',
                                fontWeight: 600,
                                fontSize: '11px',
                                textTransform: 'uppercase',
                                letterSpacing: '0.5px',
                                color: '#374151',
                                background: '#f3f4f6',
                                borderBottom: '2px solid #d1d5db',
                                borderRight:
                                  ci < dataRows[0].cells!.length - 1 ? '1px solid #e5e7eb' : 'none',
                              }}
                            >
                              {cell}
                            </th>
                          ))}
                        </tr>
                      </thead>
                    )}
                    <tbody>
                      {dataRows.slice(isFirstRowHeader ? 1 : 0).map((row, ri) => (
                        <tr key={ri}>
                          {row.cells!.map((cell, ci) => (
                            <td
                              key={ci}
                              style={{
                                padding: '6px 12px',
                                borderBottom: '1px solid #f0f0f0',
                                borderRight:
                                  ci < row.cells!.length - 1 ? '1px solid #f0f0f0' : 'none',
                                color: '#374151',
                              }}
                            >
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            }

            // --- Blank line (spacer) ---
            if (block.type === 'blank') {
              return <div key={bi} style={{ height: '8px' }} />;
            }

            // --- Separator (standalone dashes) ---
            if (block.type === 'table-separator') {
              return (
                <hr
                  key={bi}
                  style={{ border: 'none', borderTop: '1px solid #e5e7eb', margin: '12px 0' }}
                />
              );
            }

            // --- Plain text ---
            return block.items.map((item, ii) => (
              <div
                key={`${bi}-${ii}`}
                style={{
                  fontSize: '13px',
                  color: '#374151',
                  lineHeight: '1.7',
                  marginBottom: '2px',
                }}
              >
                {item.raw}
              </div>
            ));
          })}
        </div>

        {/* Document footer */}
        <div
          style={{
            padding: '12px 40px',
            borderTop: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: '#fafbfc',
            borderRadius: '0 0 4px 4px',
          }}
        >
          <div style={{ fontSize: '10px', color: '#94a3b8' }}>
            {documentId ? `Document ID: ${documentId.slice(0, 12)}...` : 'Document Preview'}
          </div>
          <div style={{ fontSize: '10px', color: '#94a3b8' }}>Page 1 of 1</div>
        </div>
      </div>
    </div>
  );
}
