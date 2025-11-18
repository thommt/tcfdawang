export function extractChunkIssues(extra?: Record<string, unknown>): string[] {
  const raw = extra && (extra as { chunk_issues?: unknown }).chunk_issues;
  if (Array.isArray(raw)) {
    return raw.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
  }
  if (typeof raw === 'string' && raw.trim()) {
    return [raw.trim()];
  }
  return [];
}

export function extractLexemeIssues(extra?: Record<string, unknown>): string[] {
  const raw = extra && (extra as { lexeme_issues?: unknown }).lexeme_issues;
  if (Array.isArray(raw)) {
    return raw.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
  }
  if (typeof raw === 'string' && raw.trim()) {
    return [raw.trim()];
  }
  return [];
}
