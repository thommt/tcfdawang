import { defineComponent, ref, computed, onMounted, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import type { FlashcardStudyCard } from '../types/flashcard';
import { fetchDueFlashcards, reviewFlashcard } from '../api/flashcards';

type EntityFilter = 'guided' | 'chunk' | 'sentence' | 'lexeme';
type PromptLanguage = 'zh' | 'en';

const filterOptions: Array<{ value: EntityFilter; label: string }> = [
  { value: 'guided', label: '标准流程' },
  { value: 'chunk', label: '记忆块卡片' },
  { value: 'sentence', label: '句子卡片' },
  { value: 'lexeme', label: '词块卡片' }
];

const promptLanguageOptions: Array<{ value: PromptLanguage; label: string }> = [
  { value: 'zh', label: '中文提示' },
  { value: 'en', label: '英文提示' }
];

const reviewScores = [
  { label: '忘记', score: 1 },
  { label: '困难', score: 3 },
  { label: '掌握', score: 5 }
];

export default defineComponent({
  name: 'FlashcardsView',
  setup() {
    const route = useRoute();
    const router = useRouter();
    const cards = ref<FlashcardStudyCard[]>([]);
    const loading = ref(false);
    const submitting = ref(false);
    const error = ref('');
    const message = ref('');
    const entityFilter = ref<EntityFilter>('guided');
    const answerFilterId = ref<number | null>(null);
    const currentIndex = ref(0);
    const promptLanguage = ref<PromptLanguage>('zh');
    const userAnswer = ref('');
    const showAnswer = ref(false);

    const currentCard = computed(() => cards.value[currentIndex.value] ?? null);
    const cardCount = computed(() => cards.value.length);
    const preferredLanguage = computed(() => promptLanguage.value);

    async function loadCards() {
      loading.value = true;
      error.value = '';
      message.value = '';
      try {
        if (entityFilter.value === 'guided') {
          cards.value = await fetchDueFlashcards({
            mode: 'guided',
            answerId: answerFilterId.value ?? undefined
          });
        } else {
          cards.value = await fetchDueFlashcards({
            mode: 'manual',
            entityType: entityFilter.value,
            answerId: answerFilterId.value ?? undefined
          });
        }
        currentIndex.value = 0;
      } catch (err) {
        error.value = '无法加载抽认卡列表';
        console.error(err);
      } finally {
        loading.value = false;
      }
    }

    function changeFilter(value: EntityFilter) {
      if (entityFilter.value === value) return;
      entityFilter.value = value;
      const query: Record<string, string> = {};
      if (value !== 'guided') {
        query.type = value;
      }
      if (answerFilterId.value !== null) {
        query.answerId = String(answerFilterId.value);
      }
      router.replace({ name: 'flashcards', query });
      loadCards();
    }

    async function handleReview(score: number) {
      const card = currentCard.value;
      if (!card || submitting.value || !showAnswer.value) return;
      submitting.value = true;
      error.value = '';
      try {
        await reviewFlashcard(card.card.id, score);
        message.value = '已记录复习结果';
        await loadCards();
      } catch (err) {
        error.value = '提交复习结果失败';
        console.error(err);
      } finally {
        submitting.value = false;
      }
    }

    function pickTranslation(
      payload: Record<'translation_en' | 'translation_zh', string | null | undefined> | null | undefined,
      lang: PromptLanguage
    ) {
      if (!payload) return null;
      const key = lang === 'zh' ? 'translation_zh' : 'translation_en';
      const value = payload[key];
      return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
    }

    const promptText = computed(() => {
      const card = currentCard.value;
      if (!card) return '暂无提示';
      const prefer = preferredLanguage.value;
      const fallback = prefer === 'zh' ? 'en' : 'zh';
      const sources: Array<Record<'translation_en' | 'translation_zh', string | null | undefined>> = [];

      if (card.card.entity_type === 'chunk' && card.chunk) {
        sources.push({
          translation_en: card.chunk.translation_en ?? null,
          translation_zh: card.chunk.translation_zh ?? null
        });
        if (card.chunk.sentence) {
          sources.push({
            translation_en: card.chunk.sentence.translation_en ?? null,
            translation_zh: card.chunk.sentence.translation_zh ?? null
          });
        }
      }
      if (card.card.entity_type === 'sentence' && card.sentence) {
        sources.push({
          translation_en: card.sentence.translation_en ?? null,
          translation_zh: card.sentence.translation_zh ?? null
        });
      }
      if (card.card.entity_type === 'lexeme' && card.lexeme) {
          sources.push({
            translation_en: card.lexeme.translation_en ?? card.lexeme.gloss ?? null,
            translation_zh: card.lexeme.translation_zh ?? card.lexeme.gloss ?? null
          });
      }
      // 如果上述都没有覆盖，则尝试其它可用信息
      if (sources.length === 0) {
        if (card.sentence) {
          sources.push({
            translation_en: card.sentence.translation_en ?? null,
            translation_zh: card.sentence.translation_zh ?? null
          });
        }
        if (card.chunk) {
          sources.push({
            translation_en: card.chunk.translation_en ?? null,
            translation_zh: card.chunk.translation_zh ?? null
          });
        }
        if (card.lexeme) {
          sources.push({
            translation_en: card.lexeme.translation_en ?? card.lexeme.gloss ?? null,
            translation_zh: card.lexeme.translation_zh ?? card.lexeme.gloss ?? null
          });
        }
      }

      const choose = (lang: PromptLanguage) => {
        for (const src of sources) {
          const found = pickTranslation(src, lang);
          if (found) return found;
        }
        return null;
      };

      return (
        choose(prefer) ||
        choose(fallback as PromptLanguage) ||
        '暂无可用提示，请直接凭记忆输入法语原文。'
      );
    });

    function confirmReveal() {
      if (!currentCard.value) return;
      showAnswer.value = true;
    }

    function renderSentenceCard() {
      const card = currentCard.value;
      if (!card?.sentence) return null;
      const { sentence } = card;
      return (
        <div class="card-section">
          <h3>句子卡片</h3>
          <p class="card__text">{sentence.text}</p>
          <p class="card__translation">英文：{sentence.translation_en ?? '—'}</p>
          <p class="card__translation">中文：{sentence.translation_zh ?? '—'}</p>
          <p class="card__meta">
            难度：{sentence.difficulty ?? '未标注'} · 段落 #{sentence.paragraph_id}
            {sentence.answer_id && (
              <>
                {' · '}
                <RouterLink to={`/answers/${sentence.answer_id}`}>查看答案</RouterLink>
              </>
            )}
          </p>
        </div>
      );
    }

    function renderLexemeCard() {
      const card = currentCard.value;
      if (!card?.lexeme) return null;
      const { lexeme } = card;
      return (
        <div class="card-section">
          <h3>词块卡片</h3>
          <p class="card__text">
            {lexeme.headword} {lexeme.sense_label && <small>({lexeme.sense_label})</small>}
          </p>
          {lexeme.gloss && <p class="card__translation">释义：{lexeme.gloss}</p>}
          <p class="card__translation">英文：{lexeme.translation_en ?? '—'}</p>
          <p class="card__translation">中文：{lexeme.translation_zh ?? '—'}</p>
          {lexeme.sample_chunk && <p class="card__meta">所在记忆块：{lexeme.sample_chunk}</p>}
          {lexeme.sample_sentence && (
            <p class="card__meta">
              示例：{lexeme.sample_sentence}
              {lexeme.sample_sentence_translation && ` · ${lexeme.sample_sentence_translation}`}
            </p>
          )}
        </div>
      );
    }

    function renderChunkCard() {
      const card = currentCard.value;
      if (!card?.chunk) return null;
      const { chunk } = card;
      const sentence = chunk.sentence;
      return (
        <div class="card-section">
          <h3>记忆块卡片</h3>
          <p class="card__text">
            #{chunk.order_index} · {chunk.text}
          </p>
          <p class="card__translation">英文：{chunk.translation_en ?? '—'}</p>
          <p class="card__translation">中文：{chunk.translation_zh ?? '—'}</p>
          <p class="card__meta">
            类型：{chunk.chunk_type ?? '未标注'}
            {sentence && (
              <>
                {' · '}
                来源句子：{sentence.text}
                {sentence.answer_id && (
                  <>
                    {' · '}
                    <RouterLink to={`/answers/${sentence.answer_id}`}>查看答案</RouterLink>
                  </>
                )}
              </>
            )}
          </p>
        </div>
      );
    }

    function setPromptLanguage(lang: PromptLanguage) {
      if (promptLanguage.value === lang) return;
      promptLanguage.value = lang;
    }

    function syncFilterFromRoute() {
      const queryType = route.query.type;
      if (queryType === 'lexeme' || queryType === 'sentence' || queryType === 'chunk') {
        entityFilter.value = queryType;
      } else {
        entityFilter.value = 'guided';
      }
      const queryAnswer = route.query.answerId;
      if (typeof queryAnswer === 'string' && queryAnswer.trim().length > 0) {
        const parsed = Number(queryAnswer);
        answerFilterId.value = Number.isFinite(parsed) ? parsed : null;
      } else {
        answerFilterId.value = null;
      }
    }

    watch(
      () => currentCard.value?.card.id,
      () => {
        userAnswer.value = '';
        showAnswer.value = false;
      },
      { immediate: true }
    );

    onMounted(() => {
      syncFilterFromRoute();
      loadCards();
    });

    watch(
      () => route.query.type,
      () => {
        syncFilterFromRoute();
        loadCards();
      }
    );
    watch(
      () => route.query.answerId,
      () => {
        syncFilterFromRoute();
        loadCards();
      }
    );

    function clearAnswerFilter() {
      answerFilterId.value = null;
      const query = entityFilter.value === 'guided' ? {} : { type: entityFilter.value };
      router.replace({ name: 'flashcards', query });
      loadCards();
    }

    return () => (
      <section class="flashcards-view">
        <header class="flashcards-view__header">
          <div>
            <h2>抽认卡训练</h2>
            <p>根据句子或词块进行快速复习，默认优先展示到期的卡片。</p>
          </div>
          <div class="flashcards-view__actions">
            {filterOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                class={['filter-button', { active: entityFilter.value === option.value }]}
                onClick={() => changeFilter(option.value)}
                disabled={loading.value}
              >
                {option.label}
              </button>
            ))}
            <button type="button" onClick={loadCards} disabled={loading.value}>
              刷新
            </button>
            <RouterLink to="/questions">返回题库</RouterLink>
          </div>
        </header>
        {answerFilterId.value !== null && (
          <p class="notice">
            当前仅复习答案 #{answerFilterId.value}
            <button type="button" onClick={clearAnswerFilter} disabled={loading.value}>
              清除限制
            </button>
          </p>
        )}
        {error.value && <p class="error">{error.value}</p>}
        {message.value && <p class="success">{message.value}</p>}
        {loading.value && <p>加载中...</p>}
        {!loading.value && cardCount.value === 0 && <p>暂无到期的抽认卡，请稍后再试。</p>}
        {!loading.value && currentCard.value && (
          <article class="flashcard-card">
            <div class="card__status">
              <span>
                进度：{currentIndex.value + 1}/{cardCount.value}
              </span>
              <span>下次复习：{new Date(currentCard.value.card.due_at).toLocaleString()}</span>
            </div>
            <div class="card__prompt">
              <div class="prompt__controls">
                <span>提示语言：</span>
                {promptLanguageOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    class={['filter-button', { active: promptLanguage.value === option.value }]}
                    onClick={() => setPromptLanguage(option.value)}
                    disabled={showAnswer.value}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <p class="prompt__text">{promptText.value}</p>
              <textarea
                class="prompt__input"
                placeholder="请输入对应的法语表达..."
                value={userAnswer.value}
                onInput={(event) => {
                  userAnswer.value = (event.target as HTMLTextAreaElement).value;
                }}
                rows={3}
                disabled={showAnswer.value}
              />
              {!showAnswer.value && (
                <button type="button" onClick={confirmReveal} class="prompt__confirm" disabled={!currentCard.value}>
                  确认查看答案
                </button>
              )}
            </div>
            {showAnswer.value && (
              <>
                {renderChunkCard()}
                {renderSentenceCard()}
                {renderLexemeCard()}
                <footer class="card__actions">
                  {reviewScores.map((item) => (
                    <button
                      key={item.score}
                      type="button"
                      onClick={() => handleReview(item.score)}
                      disabled={submitting.value}
                    >
                      {item.label}
                    </button>
                  ))}
                </footer>
              </>
            )}
          </article>
        )}
      </section>
    );
  }
});
