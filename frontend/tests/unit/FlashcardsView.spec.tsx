import { defineComponent, reactive } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi, afterEach } from 'vitest';

import FlashcardsView from '../../src/views/FlashcardsView';
import type { FlashcardStudyCard } from '../../src/types/flashcard';
import * as flashcardApi from '../../src/api/flashcards';

const routeMock = reactive({ query: { type: 'chunk' } });
const routerMock = { replace: vi.fn() };

vi.mock('vue-router', () => ({
  useRoute: () => routeMock,
  useRouter: () => routerMock,
  RouterLink: defineComponent({
    name: 'RouterLinkStub',
    props: ['to'],
    setup(_, { slots }) {
      return () => slots.default?.();
    },
  }),
}));

const buildChunkCard = (): FlashcardStudyCard => ({
  card: {
    id: 1,
    entity_type: 'chunk',
    entity_id: 42,
    last_score: null,
    due_at: new Date().toISOString(),
    streak: 0,
    interval_days: 1,
    extra: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  chunk: {
    id: 42,
    sentence_id: 7,
    order_index: 1,
    text: 'il faut s’adapter',
    translation_en: 'we must adapt',
    translation_zh: '必须适应',
    chunk_type: 'expression',
    sentence: {
      id: 7,
      paragraph_id: 2,
      answer_id: 5,
      text: 'Il faut s’adapter pour réussir',
      translation_en: 'We must adapt to succeed',
      translation_zh: '必须适应才能成功',
      difficulty: 'B2',
    },
  },
});

describe('FlashcardsView', () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    routerMock.replace.mockClear();
    routeMock.query.type = 'chunk';
    fetchSpy = vi.spyOn(flashcardApi, 'fetchDueFlashcards').mockResolvedValue([buildChunkCard()]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('defaults to chunk filter and renders chunk data', async () => {
    const wrapper = mount(FlashcardsView);
    await flushPromises();
    expect(fetchSpy).toHaveBeenCalledWith('chunk');
    expect(wrapper.text()).toContain('记忆块卡片');
    expect(wrapper.text()).toContain('il faut s’adapter');
  });

  it('switches to lexeme filter when button is clicked', async () => {
    const wrapper = mount(FlashcardsView);
    await flushPromises();
    fetchSpy.mockClear();
    const lexemeButton = wrapper
      .findAll('button.filter-button')
      .find((button) => button.text() === '词块卡片');
    expect(lexemeButton).toBeTruthy();
    await lexemeButton?.trigger('click');
    await flushPromises();
    expect(fetchSpy).toHaveBeenCalledWith('lexeme');
  });
});
