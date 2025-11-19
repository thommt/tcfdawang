import { defineComponent, ref, onMounted, watch, computed } from 'vue';
import { useRoute, useRouter, RouterLink } from 'vue-router';
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
    const router = useRouter();
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

    const showFinalize = ref(false);
    const answerTitle = ref('');
    const answerText = ref('');
    const deletingSession = ref(false);
    const deleteError = ref('');

    const session = computed<Session | null>(() => sessionStore.currentSession);
    const sessionCompleted = computed(() => session.value?.status === 'completed');
    const currentPhase = computed(() => {
      const raw = session.value?.progress_state?.phase as string | undefined;
      return raw || 'draft';
    });
    const phaseStatus = computed(() => {
      const raw = session.value?.progress_state?.phase_status as string | undefined;
      return raw || 'idle';
    });
    const phaseError = computed(() => session.value?.progress_state?.phase_error as string | undefined);
    const phaseIsRunning = computed(() => phaseStatus.value === 'running');
    const phaseIsFailed = computed(() => phaseStatus.value === 'failed');
    const showDebug = ref(false);
    const sessionHistory = computed(() => sessionStore.history);
    const historyTasks = computed(() => sessionHistory.value?.tasks ?? []);
    const historyLoading = computed(() => sessionStore.historyLoading);
    const evalHistory = computed(() =>
      sessionHistory.value ? sessionHistory.value.tasks.filter((task) => task.type === 'eval') : []
    );
    const composeHistory = computed(() =>
      sessionHistory.value ? sessionHistory.value.tasks.filter((task) => task.type === 'compose') : []
    );
    const conversations = computed(() => sessionHistory.value?.conversations ?? []);
    const canEditDraft = computed(() => {
      const current = session.value;
      if (!current) return false;
      return !current.answer_id && !sessionCompleted.value && !phaseIsRunning.value;
    });
    const canDeleteSession = computed(() => {
      const current = session.value;
      if (!current) return false;
      return !current.answer_id;
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
        savedAt: evalData.saved_at as string | undefined,
        raw: evalData,
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
          loadReviewSource(reviewSourceId.value);
        }
      }
    );

    const lastCompose = computed(() => {
      const compose = session.value?.progress_state?.last_compose as Record<string, unknown> | undefined;
      if (!compose) return null;
      return {
        title: compose.title as string | undefined,
        text: compose.text as string | undefined,
        outline: compose.outline as string | undefined,
        notes: compose.notes as string | undefined,
        savedAt: compose.saved_at as string | undefined,
        raw: compose,
      };
    });

    async function saveDraft() {
      if (!session.value || !canEditDraft.value) return;
      saving.value = true;
      try {
        await sessionStore.saveDraft(session.value.id, draft.value);
      } finally {
        saving.value = false;
      }
    }

    async function evaluate() {
      if (!session.value || phaseIsRunning.value) return;
      evalRunning.value = true;
      try {
        await sessionStore.triggerEval(session.value.id);
      } finally {
        evalRunning.value = false;
      }
    }

    const composing = ref(false);

    async function composeAnswer() {
      if (!session.value || !lastEval.value || phaseIsRunning.value) return;
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
      if (sessionCompleted.value || phaseIsRunning.value) return;
      showFinalize.value = true;
      answerTitle.value = question.value?.title ?? '';
      answerText.value = draft.value;
    }

    async function finalize() {
      if (!session.value || phaseIsRunning.value) return;
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

    async function markLearningDone() {
      if (!session.value || phaseIsRunning.value) return;
      await sessionStore.completeLearning(session.value.id);
    }

    async function deleteCurrentSession() {
      const current = session.value;
      if (!current || !canDeleteSession.value) return;
      if (!window.confirm('确定删除该 Session 吗？该操作不可恢复。')) {
        return;
      }
      deletingSession.value = true;
      deleteError.value = '';
      const redirectQuestionId = current.question_id;
      try {
        await sessionStore.deleteSession(current.id);
        if (redirectQuestionId) {
          await router.push(`/questions/${redirectQuestionId}`);
        } else {
          await router.push('/questions');
        }
      } catch (err) {
        deleteError.value = '删除 Session 失败';
        console.error(err);
      } finally {
        deletingSession.value = false;
      }
    }

    onMounted(() => {
      loadData();
    });

    return () => (
      <section class="session-workspace">
        <RouterLink class="link" to={`/questions/${question.value?.id ?? ''}`}>
          ← 返回题目详情
        </RouterLink>
        {question.value && (
          <header class="question-meta">
            <h2>{question.value.title}</h2>
            <p>
              {question.value.year}/{question.value.month} · {question.value.type}
            </p>
          </header>
        )}
        {deleteError.value && <p class="error">{deleteError.value}</p>}
        {session.value && (
          <div class="session-toolbar">
            <span>
              Session #{session.value.id} · 阶段状态：{phaseStatus.value}
              {phaseError.value && <em class="error"> · {phaseError.value}</em>}
            </span>
            {canDeleteSession.value ? (
              <button type="button" onClick={deleteCurrentSession} disabled={deletingSession.value}>
                {deletingSession.value ? '删除中...' : '删除当前 Session'}
              </button>
            ) : (
              <small>仅未关联答案的 Session 支持删除</small>
            )}
          </div>
        )}
        {isReviewSession.value && (
          <section class="review-context">
            <h3>复习模式</h3>
            <p>此 Session 基于已有答案生成，请在原答案基础上优化、扩展并记录新的思路。</p>
            {reviewSourceLoading.value && <p>源答案加载中...</p>}
            {reviewSourceError.value && <p class="error">{reviewSourceError.value}</p>}
            {reviewSourceAnswer.value && (
              <article class="source-answer-card">
                <header>
                  <strong>原答案：{reviewSourceAnswer.value.title}</strong>
                  <RouterLink to={`/answers/${reviewSourceAnswer.value.id}`} class="link">
                    查看详情
                  </RouterLink>
                </header>
                <p>
                  版本：V{reviewSourceAnswer.value.version_index} · 创建时间：
                  {new Date(reviewSourceAnswer.value.created_at).toLocaleString()}
                </p>
                {reviewComparison.value && (
                  <ul class="comparison-stats">
                    <li>
                      词数：{reviewComparison.value.currentWords}（当前） / {reviewComparison.value.sourceWords}（原文） ·
                      差值 {reviewComparison.value.diffWords >= 0 ? '+' : ''}
                      {reviewComparison.value.diffWords}
                    </li>
                    <li>
                      字符：{reviewComparison.value.currentChars}（当前） / {reviewComparison.value.sourceChars}（原文） ·
                      差值 {reviewComparison.value.diffChars >= 0 ? '+' : ''}
                      {reviewComparison.value.diffChars}
                    </li>
                  </ul>
                )}
                <details>
                  <summary>展开原文</summary>
                  <pre>{reviewSourceAnswer.value.text}</pre>
                </details>
              </article>
            )}
          </section>
        )}

        <section class="workspace">
          <div class="phase-indicator">
            当前阶段：<strong>{currentPhase.value}</strong>
            {currentPhase.value === 'draft' && <span class="hint">请先撰写草稿并请求评估</span>}
            {currentPhase.value === 'await_new_group' && <span class="hint">建议创建新的答案组</span>}
            {currentPhase.value === 'await_finalize' && <span class="hint">可根据范文生成最终答案</span>}
            {currentPhase.value === 'learning' && <span class="hint">请完成 chunk/句子学习后点击完成</span>}
            {currentPhase.value === 'completed' && <span class="hint">本次学习已完成</span>}
            <span class="phase-status">状态：{phaseStatus.value}</span>
            {phaseIsRunning.value && <span class="hint warning">当前阶段任务执行中，请稍候...</span>}
            {phaseIsFailed.value && (
              <span class="error">
                {phaseError.value ? `任务失败：${phaseError.value}` : '任务失败，请在调试面板重试。'}
              </span>
            )}
          </div>
          <label>
            <span>草稿</span>
            <textarea
              rows={8}
              value={draft.value}
              onInput={(event) => {
                draft.value = (event.target as HTMLTextAreaElement).value;
              }}
              placeholder="在此输入你的答案草稿"
              disabled={!canEditDraft.value}
            ></textarea>
          </label>
          <div class="actions">
            <button onClick={saveDraft} disabled={saving.value || !canEditDraft.value}>
              {saving.value ? '保存中...' : '保存草稿'}
            </button>
            <button
              onClick={evaluate}
              disabled={
                evalRunning.value || sessionCompleted.value || currentPhase.value !== 'draft' || phaseIsRunning.value
              }
            >
              {evalRunning.value ? '评估中...' : '请求评估'}
            </button>
            <button
              onClick={composeAnswer}
              disabled={
                composing.value ||
                sessionCompleted.value ||
                !lastEval.value ||
                (currentPhase.value !== 'await_finalize' && currentPhase.value !== 'await_new_group') ||
                phaseIsRunning.value
              }
              title={
                !lastEval.value ? '请先完成评估' : currentPhase.value === 'draft' ? '当前阶段不可生成' : ''
              }
            >
              {composing.value ? '生成中...' : 'LLM 生成答案'}
            </button>
            <button type="button" onClick={openFinalize} disabled={sessionCompleted.value || phaseIsRunning.value}>
              {sessionCompleted.value ? '已完成' : '完成 Session'}
            </button>
            {currentPhase.value === 'learning' && (
              <button
                type="button"
                onClick={markLearningDone}
                disabled={sessionCompleted.value || phaseIsRunning.value}
              >
                标记学习完成
              </button>
            )}
          </div>
        </section>
        <section class="debug-panel">
          <button type="button" onClick={() => (showDebug.value = !showDebug.value)}>
            {showDebug.value ? '收起调试' : '调试/手动操作'}
          </button>
          {showDebug.value && session.value && (
            <div class="debug-actions">
              <p>当前 phase: {currentPhase.value}</p>
              <div class="debug-buttons">
                <button onClick={() => sessionStore.triggerEval(session.value!.id)} disabled={phaseIsRunning.value}>
                  手动评估
                </button>
                <button onClick={() => sessionStore.triggerCompare(session.value!.id)} disabled={phaseIsRunning.value}>
                  对比答案组
                </button>
                <button onClick={() => sessionStore.triggerGapHighlight(session.value!.id)} disabled={phaseIsRunning.value}>
                  GapHighlighter
                </button>
                <button onClick={() => sessionStore.triggerRefine(session.value!.id)} disabled={phaseIsRunning.value}>
                  Refine Answer
                </button>
              </div>
              <div class="debug-info">
                <h4>最近任务</h4>
                <ul>
                  {historyTasks.value.slice(0, 5).map((task) => (
                    <li key={task.id}>
                      #{task.id} · {task.type} · {task.status}
                      {task.error_message && <span class="error"> · {task.error_message}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </section>
        <section class="feedback-panel">
          <h3>最近评估反馈</h3>
          {lastEval.value ? (
            <article>
              <p>
                得分：{lastEval.value.score ?? '暂无'} · 时间：
                {lastEval.value.savedAt ? new Date(lastEval.value.savedAt).toLocaleString() : '未知'}
              </p>
              <p>反馈：{lastEval.value.feedback ?? '无'}</p>
              <details>
                <summary>查看评估详情</summary>
                <pre>{JSON.stringify(lastEval.value.raw, null, 2)}</pre>
              </details>
            </article>
          ) : (
            <p>尚未请求评估。</p>
          )}
        </section>
        <section class="feedback-panel">
          <h3>最近 LLM 生成</h3>
          {lastCompose.value ? (
            <article>
              <p>
                时间：{lastCompose.value.savedAt ? new Date(lastCompose.value.savedAt).toLocaleString() : '未知'}
              </p>
              {lastCompose.value.title && <p>建议标题：{lastCompose.value.title}</p>}
              {lastCompose.value.text && (
                <blockquote>
                  <pre>{lastCompose.value.text}</pre>
                </blockquote>
              )}
              <details>
                <summary>查看生成 JSON</summary>
                <pre>{JSON.stringify(lastCompose.value.raw, null, 2)}</pre>
              </details>
            </article>
          ) : (
            <p>尚未进行 LLM 生成。</p>
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
