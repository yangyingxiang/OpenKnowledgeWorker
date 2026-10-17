/**
 * Pure string → HTML helpers used by the PDD viewer.
 *
 * All helpers HTML-escape their input before adding markup, and the output is
 * rendered with dangerouslySetInnerHTML. Inline `style="..."` attributes are used
 * (rather than Tailwind classes) because these strings are produced at runtime.
 */

export function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/* ─── PDL Syntax Highlighter ─────────────────────────────────── */

export function highlightPdl(code: string): string {
  return code
    .split('\n')
    .map((line) => {
      let h = escapeHtml(line);
      // Strings
      h = h.replace(/"([^"]*)"/g, '<span style="color:#98c379">"$1"</span>');
      // Multi-word keywords
      for (const kw of ['FOR EACH', 'ELSE IF', 'IS EMPTY', 'IS NOT', 'SIMILAR_TO']) {
        h = h.replace(
          new RegExp(kw.replace(/ /g, '\\s+'), 'g'),
          `<span style="color:#c678dd;font-weight:bold">${kw}</span>`,
        );
      }
      // Single-word keywords
      h = h.replace(
        /\b(GIVEN|SET|RETURN|DECIDE|ELSE|IF|IN|AND|OR|NOT)\b/g,
        '<span style="color:#c678dd;font-weight:bold">$1</span>',
      );
      // Built-ins
      h = h.replace(/\b(ABS|SUM|AVG|MIN|MAX)\b/g, '<span style="color:#e5c07b">$1</span>');
      // Booleans & numbers
      h = h.replace(/\b(TRUE|FALSE)\b/g, '<span style="color:#d19a66">$1</span>');
      h = h.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span style="color:#d19a66">$1</span>');
      return h;
    })
    .join('\n');
}

/* ─── Inline markdown ────────────────────────────────────────── */

/** Render inline markdown (bold, italic, code) plus [source: …] / [TENTATIVE] / [CONFIRMED] badges. */
export function renderInline(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(
      /`([^`]+)`/g,
      '<code style="background:#f0eeeb;padding:1px 5px;border-radius:3px;font-size:0.85em">$1</code>',
    )
    .replace(
      /\[source:\s*([^\]]+)\]/g,
      '<span style="display:inline-block;font-size:10px;padding:1px 6px;border-radius:3px;background:rgba(59,130,246,.1);color:#2563eb;font-family:monospace;cursor:help;margin:0 2px" title="Source: $1">$1</span>',
    )
    .replace(
      /\[TENTATIVE([^\]]*)\]/g,
      '<span style="display:inline-block;font-size:10px;padding:1px 6px;border-radius:3px;background:rgba(234,179,8,.15);color:#a16207;font-weight:600;margin:0 2px">TENTATIVE$1</span>',
    )
    .replace(
      /\[CONFIRMED([^\]]*)\]/g,
      '<span style="display:inline-block;font-size:10px;padding:1px 6px;border-radius:3px;background:rgba(34,197,94,.15);color:#15803d;font-weight:600;margin:0 2px">CONFIRMED$1</span>',
    );
}

/** Render a multi-paragraph description: blank-line separated paragraphs → <p> elements. */
export function renderDesc(text: string): string {
  return text
    .split('\n\n')
    .filter((p) => p.trim())
    .map(
      (p) =>
        `<p style="margin:0.35rem 0;line-height:1.65">${renderInline(p.trim().replace(/\n/g, ' '))}</p>`,
    )
    .join('');
}

/* ─── Fallback Markdown Renderer ─────────────────────────────── */

/** Minimal markdown → HTML used when the content can't be parsed as a structured PDD. */
export function fallbackMarkdown(md: string): string {
  let h = escapeHtml(md);
  h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
  h = h.replace(/```[\s\S]*?```/g, (m) => {
    const code = m.replace(/```\w*\n?/, '').replace(/```$/, '');
    return `<pre><code>${code}</code></pre>`;
  });
  h = h.replace(
    /&lt;!-- pdl([\s\S]*?)--&gt;/g,
    (_, c) => `<pre class="pdl-block"><code>${c.trim()}</code></pre>`,
  );
  h = h.replace(/^- (.+)$/gm, '<li>$1</li>');
  h = h.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
  h = h.replace(/\|(.+)\|\n\|[-|]+\|\n((?:\|.+\|\n?)*)/g, (_, hdr, body) => {
    const ths = hdr
      .split('|')
      .filter(Boolean)
      .map((x: string) => `<th>${x.trim()}</th>`)
      .join('');
    const rows = body
      .trim()
      .split('\n')
      .map((r: string) => {
        const tds = r
          .split('|')
          .filter(Boolean)
          .map((d: string) => `<td>${d.trim()}</td>`)
          .join('');
        return `<tr>${tds}</tr>`;
      })
      .join('');
    return `<table><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`;
  });
  h = h.replace(/\n\n/g, '</p><p>');
  return `<p>${h}</p>`;
}
