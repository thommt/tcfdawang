import { defineComponent, ref, onMounted } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { fetchAnswerById } from '../api/answers';
import { fetchAnswerGroupById } from '../api/answerGroups';
import { fetchQuestionById } from '../api/questions';
import { fetchParagraphsByAnswer, runStructureTask } from '../api/paragraphs';
import type { Answer, AnswerGroup, Paragraph } from '../types/answer';
import type { Question } from '../types/question';

export default defineComponent({
  name: 'AnswerDetailView',
  setup() {
    const route = useRoute();
    const answerId = Number(route.params.id);
    const answer = ref<Answer | null>(null);
    const group = ref<AnswerGroup | null>(null);
    const question = ref<Question | null>(null);
    const loading = ref(true);
    const error = ref('');
    const paragraphs = ref<Paragraph[]>([]);
    const structuring = ref(false);
    const structureError = ref('');
    const structureMessage = ref('');

    async function loadParagraphStructure() {
      paragraphs.value = await fetchParagraphsByAnswer(answerId);
    }

    async function load() {
      loading.value = true;
      error.value = '';
      structureError.value = '';
      structureMessage.value = '';
      try {
        answer.value = await fetchAnswerById(answerId);
        group.value = await fetchAnswerGroupById(answer.value.answer_group_id);
        question.value = await fetchQuestionById(group.value.question_id);
        await loadParagraphStructure();
      } catch (err) {
        error.value = '无法加载答案详情';
        throw err;
      } finally {
        loading.value = false;
      }
    }

    async function rebuildStructure() {
      if (structuring.value) return;
      structuring.value = true;
      structureError.value = '';
      structureMessage.value = '';
      try {
        await runStructureTask(answerId);
        await loadParagraphStructure();
        structureMessage.value = '结构分析完成';
      } catch (err) {
        structureError.value = '触发结构分析失败';
        console.error(err);
      } finally {
        structuring.value = false;
      }
    }

    onMounted(() => {
      load();
    });

    return () => (
      <section class="answer-detail">
        <RouterLink to={question.value ? `/questions/${question.value.id}` : '/questions'} class="link">
          ← 返回题目
        </RouterLink>
        {loading.value && <p>加载中...</p>}
        {error.value && <p class="error">{error.value}</p>}
        {question.value && (
          <div class="question-card">
            <h2>{question.value.title}</h2>
            <p>
              {question.value.year}/{question.value.month} · {question.value.type}
            </p>
          </div>
        )}
        {group.value && (
          <p>
            答案组：<strong>{group.value.title}</strong>
          </p>
        )}
        {answer.value && (
          <article class="answer-card">
            <header>
              <h3>
                {answer.value.title} <small>版本 {answer.value.version_index}</small>
              </h3>
              <p>状态：{answer.value.status}</p>
            </header>
            <p class="timestamp">创建时间：{new Date(answer.value.created_at).toLocaleString()}</p>
            <pre>{answer.value.text}</pre>
          </article>
        )}
        <section class="paragraphs">
          <header class="paragraphs__header">
            <h4>段落结构</h4>
            <button type="button" onClick={rebuildStructure} disabled={structuring.value}>
              {structuring.value ? '分析中...' : paragraphs.value.length ? '重新生成' : '生成结构'}
            </button>
          </header>
          {structureError.value && <p class="error">{structureError.value}</p>}
          {structureMessage.value && <p class="success">{structureMessage.value}</p>}
          {paragraphs.value.length === 0 && !loading.value && <p>暂无结构化结果</p>}
          {paragraphs.value.length > 0 &&
            paragraphs.value.map((paragraph) => (
              <article key={paragraph.id} class="paragraph-card">
                <header>
                  <strong>
                    #{paragraph.order_index} {paragraph.role_label}
                  </strong>
                  {paragraph.summary && <p>{paragraph.summary}</p>}
                </header>
                <ol>
                  {paragraph.sentences.map((sentence) => (
                    <li key={sentence.id}>
                      {sentence.text}
                      {sentence.translation && <em>（{sentence.translation}）</em>}
                    </li>
                  ))}
                </ol>
              </article>
            ))}
        </section>
      </section>
    );
  },
});
