import { defineComponent, ref, onMounted, computed } from 'vue';
import { useRoute, RouterLink, useRouter } from 'vue-router';
import { fetchAnswerById, fetchAnswerHistory } from '../api/answers';
import { fetchAnswerGroupById } from '../api/answerGroups';
import { fetchQuestionById } from '../api/questions';
import { fetchParagraphsByAnswer, runStructureTask } from '../api/paragraphs';
import type { Answer, AnswerGroup, Paragraph, AnswerHistory } from '../types/answer';
import type { Question, FetchTask } from '../types/question';
import { useSessionStore } from '../stores/sessions';

export default defineComponent({
  name: 'AnswerDetailView',
  setup() {
    const route = useRoute();
    const router = useRouter();
    const sessionStore = useSessionStore();
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
    const history = ref<AnswerHistory | null>(null);
    const historyLoading = ref(false);
    const historyError = ref('');

    async function loadParagraphStructure() {
      paragraphs.value = await fetchParagraphsByAnswer(answerId);
    }

    const latestStructureTask = computed<FetchTask | null>(() => {
      if (!history.value) return null;
      return history.value.tasks.find((task) => task.type === 'structure') ?? null;
    });

    async function loadHistory() {
      historyLoading.value = true;
      historyError.value = '';
      try {
        history.value = await fetchAnswerHistory(answerId);
      } catch (err) {
        historyError.value = '无法加载历史记录';
        console.error(err);
      } finally {
        historyLoading.value = false;
      }
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
        await loadHistory();
      } catch (err) {
        error.value = '无法加载答案详情';
        throw err;
      } finally {
        loading.value = false;
      }
    }

    async function startReviewSession() {
      reviewError.value = '';
      try {
        const session = await sessionStore.createReviewSession(answerId);
        router.push(`/sessions/${session.id}`);
      } catch (err) {
        reviewError.value = '创建复习 Session 失败';
        console.error(err);
      }
    }

    async function rebuildStructure() {
      if (structuring.value) return;
      structuring.value = true;
      structureError.value = '';
      structureMessage.value = '';
      try {
        await runStructureTask(answerId);
        structureMessage.value = '结构分析完成';
      } catch (err) {
        structureError.value = '触发结构分析失败';
        console.error(err);
      } finally {
        structuring.value = false;
        await loadParagraphStructure();
        await loadHistory();
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
          <section class="answer-group-summary">
            <h4>答案组：{group.value.title}</h4>
            <p>
              版本数量：<strong>{group.value.answers.length}</strong>
            </p>
            {group.value.descriptor && (
              <p>
                主题/描述：<em>{group.value.descriptor}</em>
              </p>
            )}
            {group.value.dialogue_profile && Object.keys(group.value.dialogue_profile).length > 0 && (
              <details>
                <summary>对话设定</summary>
                <pre>{JSON.stringify(group.value.dialogue_profile, null, 2)}</pre>
              </details>
            )}
          </section>
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
            <button type="button" onClick={startReviewSession}>
              基于此答案创建复习 Session
            </button>
            {reviewError.value && <p class="error">{reviewError.value}</p>}
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
          {latestStructureTask.value && (
            <p class="structure-task-meta">
              最近一次任务：#{latestStructureTask.value.id} · {latestStructureTask.value.status} ·
              {new Date(latestStructureTask.value.updated_at).toLocaleString()}
              {latestStructureTask.value.error_message && (
                <span class="error"> 错误：{latestStructureTask.value.error_message}</span>
              )}
            </p>
          )}
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
        <section class="answer-history">
          <header>
            <h4>学习历史</h4>
          </header>
          {historyLoading.value && <p>历史加载中...</p>}
          {historyError.value && <p class="error">{historyError.value}</p>}
          {history.value && (
            <>
              <div class="history-block">
                <h5>相关 Session</h5>
                {history.value.sessions.length ? (
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>类型</th>
                        <th>状态</th>
                        <th>开始时间</th>
                        <th>完成时间</th>
                        <th>复习要点</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.value.sessions.map((session) => {
                        const reviewNotes = session.progress_state?.review_notes as string | undefined;
                        return (
                          <tr key={session.id}>
                            <td>{session.id}</td>
                            <td>{session.session_type}</td>
                            <td>{session.status}</td>
                            <td>{new Date(session.started_at).toLocaleString()}</td>
                            <td>{session.completed_at ? new Date(session.completed_at).toLocaleString() : '—'}</td>
                            <td>
                              {reviewNotes ? (
                                <span title={reviewNotes}>{reviewNotes.slice(0, 40)}{reviewNotes.length > 40 ? '…' : ''}</span>
                              ) : (
                                '—'
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <p>尚无与此答案关联的 Session。</p>
                )}
              </div>
              <div class="history-block">
                <h5>任务记录</h5>
                {history.value.tasks.length ? (
                  <table>
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>类型</th>
                        <th>状态</th>
                        <th>更新时间</th>
                        <th>错误</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.value.tasks.map((task) => (
                        <tr key={task.id}>
                          <td>{task.id}</td>
                          <td>{task.type}</td>
                          <td>{task.status}</td>
                          <td>{new Date(task.updated_at).toLocaleString()}</td>
                          <td>{task.error_message || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p>暂无任务记录。</p>
                )}
              </div>
              <div class="history-block">
                <h5>LLM 日志</h5>
                {history.value.conversations.length ? (
                  <ul class="conversation-list">
                    {history.value.conversations.map((log) => (
                      <li key={log.id}>
                        <strong>{log.purpose}</strong> · {new Date(log.created_at).toLocaleString()}
                        {log.model_name && <span> · {log.model_name}</span>}
                        <details>
                          <summary>查看详情</summary>
                          <pre>{JSON.stringify(log.result, null, 2)}</pre>
                        </details>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>暂无 LLM 日志。</p>
                )}
              </div>
            </>
          )}
        </section>
      </section>
    );
  },
});
    const reviewError = ref('');
