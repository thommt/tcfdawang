import { describe, it, expect } from 'vitest';
import { extractChunkIssues, extractLexemeIssues } from '../../src/utils/chunks';

describe('chunk issue helpers', () => {
  it('extracts chunk issues from array', () => {
    const extra = { chunk_issues: ['问题1', ' ', '问题2'] };
    expect(extractChunkIssues(extra)).toEqual(['问题1', '问题2']);
  });

  it('extracts lexeme issues from string', () => {
    const extra = { lexeme_issues: '缺少关键词' };
    expect(extractLexemeIssues(extra)).toEqual(['缺少关键词']);
  });

  it('returns empty array when no issues', () => {
    expect(extractChunkIssues()).toEqual([]);
    expect(extractLexemeIssues({})).toEqual([]);
  });
});
