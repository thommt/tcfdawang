import { defineComponent, ref, onMounted, watch, computed } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { useSessionStore } from '../stores/sessions';
import { useQuestionStore } from '../stores/questions';
import type { Session } from '../types/session';
import type { Answer } from '../types/answer';
import { fetchQuestionById } from '../api/questions';
import { fetchAnswerById } from '../api/answers';
import type { Question } from '../types/question';

export default defineComponent({
  name: 'SessionWorkspaceView',
  setup() {
    const route = useRoute();
    const sessionId = Number(route.params.id);
    const sessionStore = useSessionStore();
    const questionStore = useQuestionStore();
    const draft = ref('');
    const saving = ref(false);
    const evalRunning = ref(false);
    const finalizing = ref(false);
    const question = ref<Question | null>(null);
    const reviewSourceAnswer = ref<Answer | null>(null);
    const reviewSourceLoading = ref(false);
    const reviewSourceError = ref('');
    const reviewNotes = ref('');
    const savingReviewNotes = ref(false);
    const reviewNoteMessage = ref('');

    const showFinalize = ref(false);
    const answerTitle = ref('');
    const answerText = ref('');

    const sessionCompleted = computed(() => session.value?.status === 'completed');

    const session = computed<Session | null>(() => sessionStore.currentSession);
    const sessionHistory = computed(() => sessionStore.history);
    const historyLoading = computed(() => sessionStore.historyLoading);
    const evalHistory = computed(() =>
      sessionHistory.value ? sessionHistory.value.tasks.filter((task) => task.type === 'eval') : []
    );
    const composeHistory = computed(() =>
      sessionHistory.value ? sessionHistory.value.tasks.filter((task) => task.type === 'compose') : []
    );
    const conversations = computed(() => sessionHistory.value?.conversations ?? []);
    const reviewNotesHistory = computed(() => {
      const entries = sessionHistory.value?.session.progress_state?.review_notes_history;
      if (!entries || !Array.isArray(entries)) {
        return [];
      }
      return entries as Array<{ note: string; saved_at: string }>;
    });
    const isReviewSession = computed(() => session.value?.session_type === 'review');
    const reviewSourceId = computed(() => {
      const current = session.value;
      if (!current) return null;
      const fromState = (current.progress_state?.review_source_answer_id as number | undefined) ?? null;
      return fromState || current.answer_id || null;
    });
    const reviewComparison = computed(() => {
      if (!reviewSourceAnswer.value) return null;
      const baseText = reviewSourceAnswer.value.text || '';
      const currentText = draft.value || '';
      const countWords = (text: string) => {
        const trimmed = text.trim();
        return trimmed ? trimmed.split(/\s+/).length : 0;
      };
      const sourceWords = countWords(baseText);
      const currentWords = countWords(currentText);
      const sourceChars = baseText.length;
      const currentChars = currentText.length;
      return {
        sourceWords,
        currentWords,
        diffWords: currentWords - sourceWords,
        sourceChars,
        currentChars,
        diffChars: currentChars - sourceChars,
      };
    });
    const lastEval = computed(() => {
      const evalData = session.value?.progress_state?.last_eval as Record<string, unknown> | undefined;
      if (!evalData) return null;
      return {
        feedback: evalData.feedback as string | undefined,
        score: evalData.score as number | undefined,
      };
    });

    async function loadReviewSource(answerId: number | null) {
      if (!answerId) {
        reviewSourceAnswer.value = null;
        return;
      }
      reviewSourceLoading.value = true;
      reviewSourceError.value = '';
      try {
        reviewSourceAnswer.value = await fetchAnswerById(answerId);
      } catch (err) {
        reviewSourceError.value = '无法加载源答案';
        console.error(err);
      } finally {
        reviewSourceLoading.value = false;
      }
    }

    async function loadData() {
      await sessionStore.loadSession(sessionId);
      const current = sessionStore.currentSession;
      draft.value = current?.user_answer_draft ?? '';
      reviewNotes.value = (current?.progress_state?.review_notes as string | undefined) ?? '';
      if (current) {
        const existing = questionStore.items.find((item) => item.id === current.question_id);
        if (existing) {
          question.value = existing;
        } else {
          question.value = await fetchQuestionById(current.question_id);
        }
        await loadReviewSource(reviewSourceId.value);
      }
      await sessionStore.loadSessionHistory(sessionId);
    }

    watch(
      () => sessionStore.currentSession,
      (value) => {
        if (value) {
          draft.value = value.user_answer_draft ?? '';
          reviewNotes.value = (value.progress_state?.review_notes as string | undefined) ?? '';
          reviewNoteMessage.value = '';
          loadReviewSource(reviewSourceId.value);
        }
      }
    );

    const lastCompose = computed(() => {
      const compose = session.value?.progress_state?.last_compose as Record<string, unknown> | undefined;
      return compose ?? null;
    });

    async function saveDraft() {
      if (!session.value) return;
      saving.value = true;
      try {
        await sessionStore.saveDraft(session.value.id, draft.value);
      } finally {
        saving.value = false;
      }
    }

    async function saveReviewNote() {
      if (!session.value) return;
      savingReviewNotes.value = true;
      reviewNoteMessage.value = '';
      try {
        await sessionStore.saveReviewNotes(session.value.id, reviewNotes.value);
        reviewNoteMessage.value = '已保存改进要点';
      } catch (err) {
        reviewNoteMessage.value = '保存失败，请重试';
        console.error(err);
      } finally {
        savingReviewNotes.value = false;
      }
    }

    async function evaluate() {
      if (!session.value) return;
      evalRunning.value = true;
      try {
        await sessionStore.triggerEval(session.value.id);
      } finally {
        evalRunning.value = false;
      }
    }

    const composing = ref(false);

    async function composeAnswer() {
      if (!session.value) return;
      composing.value = true;
      try {
        const task = await sessionStore.composeAnswer(session.value.id);
        const summary = task.result_summary as Record<string, string>;
        answerTitle.value = summary?.title ?? question.value?.title ?? '';
        answerText.value = summary?.text ?? draft.value;
        showFinalize.value = true;
      } finally {
        composing.value = false;
      }
    }

    function openFinalize() {
      if (sessionCompleted.value) return;
      showFinalize.value = true;
      answerTitle.value = question.value?.title ?? '';
      answerText.value = draft.value;
    }

    async function finalize() {
      if (!session.value) return;
      finalizing.value = true;
      try {
        await sessionStore.finalizeSession(session.value.id, {
          answer_title: answerTitle.value || '最终答案',
          answer_text: answerText.value || draft.value,
        });
        showFinalize.value = false;
      } finally {
        finalizing.value = false;
      }
    }

    onMounted(() => {
      loadData();
    });

            </ul>
          )}
        </section>
        <section class="history-panel">
          <h3>任务列表</h3>
          {historyLoading.value && <p>加载中...</p>}
          {!historyLoading.value && sessionHistory.value && sessionHistory.value.tasks.length === 0 && <p>暂无任务。</p>}
          {!historyLoading.value && sessionHistory.value && sessionHistory.value.tasks.length > 0 && (
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
                {sessionHistory.value.tasks.map((task) => (
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
          )}
        </section>
        {isReviewSession.value && (
          <section class="history-panel">
            <h3>改进历史</h3>
            {historyLoading.value && <p>加载中...</p>}
            {!historyLoading.value && reviewNotesHistory.value.length === 0 && <p>尚无改进记录。</p>}
            {!historyLoading.value && reviewNotesHistory.value.length > 0 && (
              <ul class="history-list">
                {reviewNotesHistory.value.map((entry, index) => (
                  <li key={`${entry.saved_at}-${index}`}>
                    <header>{new Date(entry.saved_at).toLocaleString()}</header>
                    <p>{entry.note || '未记录任何内容'}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}
        <section class="history-panel">
          <h3>LLM 日志</h3>
          {historyLoading.value && <p>加载中...</p>}
          {!historyLoading.value && conversations.value.length === 0 && <p>暂无 LLM 对话。</p>}
          {!historyLoading.value && conversations.value.length > 0 && (
            <ul class="conversation-list">
              {conversations.value.map((log) => (
                <li key={log.id}>
                  <strong>{log.purpose}</strong> · {new Date(log.created_at).toLocaleString()}
                  {log.model_name && <span> · {log.model_name}</span>}
                  <details>
                    <summary>查看结果</summary>
                    <pre>{JSON.stringify(log.result, null, 2)}</pre>
                  </details>
                </li>
              ))}
            </ul>
          )}
        </section>
        {showFinalize.value && (
          <section class="finalize-panel">
            <h3>确认答案</h3>
            <label>
              <span>答案标题</span>
              <input value={answerTitle.value} onInput={(e) => (answerTitle.value = (e.target as HTMLInputElement).value)} />
            </label>
            <label>
              <span>答案内容</span>
              <textarea
                rows={6}
                value={answerText.value || draft.value}
                onInput={(e) => (answerText.value = (e.target as HTMLTextAreaElement).value)}
              ></textarea>
            </label>
            <div class="actions">
              <button type="button" onClick={() => (showFinalize.value = false)}>
                取消
              </button>
              <button type="button" onClick={finalize} disabled={finalizing.value}>
                {finalizing.value ? '提交中...' : '确认并生成答案'}
              </button>
            </div>
          </section>
        )}
      </section>
    );
  },
});
