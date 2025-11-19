import { defineComponent, onMounted, ref, computed } from 'vue';
import { useRoute, RouterLink, useRouter } from 'vue-router';
import { useQuestionStore } from '../stores/questions';
import { useSessionStore } from '../stores/sessions';
import type { Question } from '../types/question';
import { fetchQuestionById } from '../api/questions';
import { fetchAnswerGroups, deleteAnswerGroup } from '../api/answerGroups';
import type { AnswerGroup } from '../types/answer';

export default defineComponent({
  name: 'QuestionDetailView',
  setup() {
    const route = useRoute();
    const questionId = Number(route.params.id);
    const router = useRouter();
    const questionStore = useQuestionStore();
    const sessionStore = useSessionStore();
    const question = ref<Question | null>(null);
    const loading = ref(true);
    const error = ref('');
    const answerGroups = ref<AnswerGroup[]>([]);
    const groupLoading = ref(false);
    const deletingGroupId = ref<number | null>(null);
    const groupError = ref('');
    const deletingSessionId = ref<number | null>(null);
    const sessionError = ref('');
    const defaultSessionLoading = ref(false);
    const defaultSessionError = ref('');

    const hasRunningSession = computed(() =>
      sessionStore
        .sessionsByQuestion(questionId)
        .some(
          (session) =>
            session.session_type === 'first' &&
            !session.answer_id &&
            (session.progress_state?.phase_status as string | undefined) === 'running'
        )
    );

    const relatedSessions = computed(() => sessionStore.sessionsByQuestion(questionId));
    const answerIdToGroupId = computed(() => {
      const map = new Map<number, number>();
      for (const group of answerGroups.value) {
        for (const answer of group.answers) {
          map.set(answer.id, group.id);
        }
      }
      return map;
    });
    const sessionsByGroup = computed(() => {
      const grouped: Record<number, typeof relatedSessions.value> = {};
      for (const session of relatedSessions.value) {
        if (!session.answer_id) continue;
        const groupId = answerIdToGroupId.value.get(session.answer_id);
        if (!groupId) continue;
        if (!grouped[groupId]) grouped[groupId] = [];
        grouped[groupId].push(session);
      }
      return grouped;
    });
    const looseSessions = computed(() =>
      relatedSessions.value.filter((session) => !session.answer_id || !answerIdToGroupId.value.get(session.answer_id))
    );

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
        groupError.value = '';
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

    async function handleDeleteGroup(groupId: number) {
      if (deletingGroupId.value) return;
      if (!window.confirm('确定要删除整个答案组及其版本吗？该操作不可恢复。')) {
        return;
      }
      deletingGroupId.value = groupId;
      groupError.value = '';
      try {
        await deleteAnswerGroup(groupId);
        await loadQuestion();
      } catch (err) {
        groupError.value = '删除答案组失败';
        console.error(err);
      } finally {
        deletingGroupId.value = null;
      }
    }

    async function handleDeleteSession(sessionId: number) {
      if (deletingSessionId.value) return;
      if (!window.confirm('确定删除该 Session 吗？该操作不可恢复。')) return;
      deletingSessionId.value = sessionId;
      sessionError.value = '';
      try {
        await sessionStore.deleteSession(sessionId);
      } catch (err) {
        sessionError.value = '删除 Session 失败';
        console.error(err);
      } finally {
        deletingSessionId.value = null;
      }
    }

    async function enterDefaultSession() {
      defaultSessionError.value = '';
      defaultSessionLoading.value = true;
      try {
        if (!sessionStore.sessions.length) {
          await sessionStore.loadSessions();
        }
        if (hasRunningSession.value) {
          defaultSessionError.value = '默认学习流程正在执行，请稍候';
          return;
        }
        let target =
          sessionStore
            .sessionsByQuestion(questionId)
            .find(
              (session) =>
                session.session_type === 'first' &&
                !session.answer_id &&
                session.status !== 'completed' &&
                (session.progress_state?.phase_status as string | undefined) !== 'running'
            ) ||
          null;
        if (!target) {
          target = await sessionStore.createSession(questionId);
        }
        const phaseStatus = (target.progress_state?.phase_status as string | undefined) ?? 'idle';
        if (phaseStatus === 'running') {
          defaultSessionError.value = '默认学习流程正在执行，请稍候';
          return;
        }
        await router.push(`/sessions/${target.id}`);
      } catch (err) {
        console.error(err);
        defaultSessionError.value = '无法进入默认学习';
      } finally {
        defaultSessionLoading.value = false;
      }
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
            <div class="question-actions">
              <button
                type="button"
                onClick={enterDefaultSession}
                disabled={defaultSessionLoading.value || hasRunningSession.value}
                title={hasRunningSession.value ? '学习流程正在执行，请稍候' : ''}
              >
                {defaultSessionLoading.value ? '进入中...' : hasRunningSession.value ? '处理中...' : '默认学习'}
              </button>
            </div>
            {defaultSessionError.value && <p class="error">{defaultSessionError.value}</p>}
          </div>
        )}

        <section class="session-list">
          <header>
            <h3>历史 Session</h3>
          </header>
          {sessionError.value && <p class="error">{sessionError.value}</p>}
          {looseSessions.value.length ? (
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
                {looseSessions.value.map((session) => {
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
                        {!session.answer_id && (
                          <button
                            type="button"
                            onClick={() => handleDeleteSession(session.id)}
                            disabled={deletingSessionId.value === session.id}
                            style="margin-left:0.5rem;"
                          >
                            删除
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <p>暂无未绑定答案组的 Session。</p>
          )}
        </section>

        <section class="answer-groups">
         <header>
           <h3>答案组</h3>
         </header>
          {groupError.value && <p class="error">{groupError.value}</p>}
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
                {sessionsByGroup.value[group.id] && sessionsByGroup.value[group.id].length > 0 && (
                  <div class="group-sessions">
                    <h5>关联 Session</h5>
                    <ul>
                      {sessionsByGroup.value[group.id].map((session) => (
                        <li key={session.id}>
                          #{session.id} · {session.status}
                          <RouterLink style="margin-left:0.5rem;" to={`/sessions/${session.id}`}>
                            查看
                          </RouterLink>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
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
                <button
                  type="button"
                  class="danger"
                  onClick={() => handleDeleteGroup(group.id)}
                  disabled={deletingGroupId.value === group.id}
                >
                  {deletingGroupId.value === group.id ? '删除中...' : '删除整个答案组'}
                </button>
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
