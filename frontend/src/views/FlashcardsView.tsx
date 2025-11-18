import { defineComponent, ref, computed, onMounted, watch } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import type { FlashcardStudyCard } from '../types/flashcard';
import { fetchDueFlashcards, reviewFlashcard } from '../api/flashcards';

type EntityFilter = 'sentence' | 'lexeme' | 'all';

const filterOptions: Array<{ value: EntityFilter; label: string }> = [
  { value: 'sentence', label: '句子卡片' },
  { value: 'lexeme', label: '词块卡片' },
  { value: 'all', label: '全部' }
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
    const entityFilter = ref<EntityFilter>('sentence');
    const currentIndex = ref(0);

    const currentCard = computed(() => cards.value[currentIndex.value] ?? null);
    const cardCount = computed(() => cards.value.length);

    async function loadCards() {
      loading.value = true;
      error.value = '';
      message.value = '';
      try {
        const filter = entityFilter.value === 'all' ? undefined : entityFilter.value;
        cards.value = await fetchDueFlashcards(filter);
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
      const query = value === 'sentence' ? {} : { type: value };
      router.replace({ name: 'flashcards', query });
      loadCards();
    }

    async function handleReview(score: number) {
      const card = currentCard.value;
      if (!card || submitting.value) return;
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

    function syncFilterFromRoute() {
      const queryType = route.query.type;
      if (queryType === 'lexeme' || queryType === 'all' || queryType === 'sentence') {
        entityFilter.value = queryType;
      } else {
        entityFilter.value = 'sentence';
      }
    }

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
          </article>
        )}
      </section>
    );
  }
});
