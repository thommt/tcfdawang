import { defineComponent, onMounted, ref, computed } from 'vue';
import { useRoute, useRouter, RouterLink } from 'vue-router';
import { useQuestionStore } from '../stores/questions';
import { useSessionStore } from '../stores/sessions';
import type { Question } from '../types/question';
import { fetchQuestionById } from '../api/questions';
import { fetchAnswerGroups } from '../api/answerGroups';
import type { AnswerGroup } from '../types/answer';

export default defineComponent({
  name: 'QuestionDetailView',
  setup() {
    const route = useRoute();
    const router = useRouter();
    const questionId = Number(route.params.id);
    const questionStore = useQuestionStore();
    const sessionStore = useSessionStore();
    const question = ref<Question | null>(null);
    const loading = ref(true);
    const error = ref('');
    const answerGroups = ref<AnswerGroup[]>([]);
    const groupLoading = ref(false);

    const relatedSessions = computed(() => sessionStore.sessionsByQuestion(questionId));

    async function loadQuestion() {
      loading.value = true;
      error.value = '';
      try {
        const existing = questionStore.items.find((item) => item.id === questionId);
        if (existing) {
          question.value = existing;
        } else {
          const fetched = await fetchQuestionById(questionId);
          question.value = fetched;
          questionStore.items.push(fetched);
        }
        groupLoading.value = true;
        answerGroups.value = await fetchAnswerGroups(questionId);
        groupLoading.value = false;
        if (!sessionStore.sessions.length) {
          await sessionStore.loadSessions();
        }
      } catch (err) {
        error.value = '无法加载题目详情';
        throw err;
      } finally {
        loading.value = false;
      }
    }

    async function createSession() {
      const session = await sessionStore.createSession(questionId);
      router.push(`/sessions/${session.id}`);
    }

    onMounted(() => {
      loadQuestion();
    });

    return () => (
      <section class="question-detail">
        <RouterLink to="/questions" class="link">
          ← 返回题目列表
        </RouterLink>
        {loading.value && <p>加载中...</p>}
        {error.value && <p class="error">{error.value}</p>}
        {question.value && (
          <div class="card">
            <h2>{question.value.title}</h2>
            <p>
              <strong>题型：</strong>
              {question.value.type}
              <strong style="margin-left: 1rem;">来源：</strong>
              {question.value.source}
            </p>
            <p>
              <strong>时间：</strong>
              {question.value.year}/{question.value.month}
            </p>
            <p class="body">{question.value.body}</p>
            <p>
              <strong>标签：</strong>
              {question.value.tags.join(', ') || '暂无'}
            </p>
            <button onClick={createSession}>创建学习 Session</button>
          </div>
        )}

        <section class="session-list">
          <header>
            <h3>历史 Session</h3>
          </header>
          {relatedSessions.value.length ? (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>类型</th>
                  <th>状态</th>
                  <th>最近反馈</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {relatedSessions.value.map((session) => {
                  const lastEval = (session.progress_state?.last_eval ?? {}) as Record<string, unknown>;
                  return (
                    <tr key={session.id}>
                      <td>{session.id}</td>
                      <td>{session.session_type}</td>
                      <td>{session.status}</td>
                      <td>
                        {'feedback' in lastEval ? `${lastEval.feedback as string} (分数: ${lastEval.score ?? '无'})` : '暂无'}
                      </td>
                      <td>
                        <RouterLink to={`/sessions/${session.id}`}>进入</RouterLink>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <p>该题目前还没有 Session。</p>
          )}
        </section>

        <section class="answer-groups">
          <header>
            <h3>答案组</h3>
          </header>
          {groupLoading.value && <p>加载答案组...</p>}
          {!groupLoading.value && answerGroups.value.length ? (
            answerGroups.value.map((group) => (
              <article key={group.id} class="answer-group">
                <h4>{group.title}</h4>
                {group.descriptor && <p>主题：{group.descriptor}</p>}
                {group.dialogue_profile && Object.keys(group.dialogue_profile).length > 0 && (
                  <details>
                    <summary>对话设定</summary>
                    <pre>{JSON.stringify(group.dialogue_profile, null, 2)}</pre>
                  </details>
                )}
                <p>共 {group.answers.length} 个版本</p>
                <ul>
                  {group.answers.map((answer) => (
                    <li key={answer.id}>
                      <strong>V{answer.version_index}:</strong> {answer.title} ·{' '}
                      {new Date(answer.created_at).toLocaleDateString()}
                      <RouterLink style="margin-left: 0.5rem;" to={`/answers/${answer.id}`}>
                        查看
                      </RouterLink>
                    </li>
                  ))}
                </ul>
              </article>
            ))
          ) : (
            !groupLoading.value && <p>暂无答案。</p>
          )}
        </section>
      </section>
    );
  },
});
