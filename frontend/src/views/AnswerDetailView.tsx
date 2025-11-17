import { defineComponent, ref, onMounted } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { fetchAnswerById } from '../api/answers';
import { fetchAnswerGroupById } from '../api/answerGroups';
import { fetchQuestionById } from '../api/questions';
import type { Answer } from '../types/answer';
import type { AnswerGroup } from '../types/answer';
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

    async function load() {
      loading.value = true;
      error.value = '';
      try {
        answer.value = await fetchAnswerById(answerId);
        group.value = await fetchAnswerGroupById(answer.value.answer_group_id);
        question.value = await fetchQuestionById(group.value.question_id);
      } catch (err) {
        error.value = '无法加载答案详情';
        throw err;
      } finally {
        loading.value = false;
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
      </section>
    );
  },
});
