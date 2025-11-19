import { defineComponent, ref, onMounted, watch, computed } from 'vue';
import { useRoute, useRouter, RouterLink } from 'vue-router';
import { useSessionStore } from '../stores/sessions';
import { useQuestionStore } from '../stores/questions';
import type { Session, SessionFinalizePayload } from '../types/session';
import type { Answer, AnswerGroup } from '../types/answer';
import type { FlashcardStudyCard } from '../types/flashcard';
import { fetchQuestionById } from '../api/questions';
import { fetchAnswerById } from '../api/answers';
import { fetchAnswerGroups } from '../api/answerGroups';
import { fetchDueFlashcards, reviewFlashcard } from '../api/flashcards';
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
    const reviewScoreOptions = [
      { label: '忘记', score: 1 },
      { label: '困难', score: 3 },
      { label: '掌握', score: 5 },
    ];
    const answerGroups = ref<AnswerGroup[]>([]);
    const groupsLoading = ref(false);
    const groupsError = ref('');
    const learningCards = ref<FlashcardStudyCard[]>([]);
    const learningLoading = ref(false);
    const learningError = ref('');
    const learningMessage = ref('');
    const learningSubmitting = ref(false);
    const learningIndex = ref(0);

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


    async function loadAnswerGroupsForQuestion(questionId: number) {
      groupsLoading.value = true;
      groupsError.value = '';
      try {
        answerGroups.value = await fetchAnswerGroups(questionId);
      } catch (err) {
        groupsError.value = '答案组加载失败';
        console.error(err);
      } finally {
        groupsLoading.value = false;
      }
    }

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
        await loadAnswerGroupsForQuestion(current.question_id);
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

    watch(
      () => answerGroups.value.length,
      (length) => {
        if (length && finalizeMode.value === 'reuse' && !selectedGroupId.value) {
          selectedGroupId.value = answerGroups.value[0].id;
        }
      }
    );

    watch(
      [currentPhase, phaseStatus, () => session.value?.answer_id],
      ([phase, status]) => {
        if (phase === 'learning') {
          if (status === 'idle') {
            loadLearningCards();
          } else if (status === 'running') {
            resetLearningState();
            learningMessage.value = '正在准备抽认卡，请稍候...';
          }
        } else {
          resetLearningState();
        }
      },
      { immediate: true }
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

    const lastCompare = computed(() => {
      const compareData = session.value?.progress_state?.last_compare as Record<string, unknown> | undefined;
      if (!compareData) return null;
      return {
        raw: compareData,
        decision: compareData.decision as string | undefined,
        matchedGroupId: compareData.matched_answer_group_id as number | undefined,
        reason: compareData.reason as string | undefined,
        differences: Array.isArray(compareData.differences)
          ? (compareData.differences as string[])
          : [],
      };
    });
    const matchedAnswerGroup = computed(() => {
      if (!lastCompare.value?.matchedGroupId) return null;
      return answerGroups.value.find((group) => group.id === lastCompare.value?.matchedGroupId) ?? null;
    });
    const composing = ref(false);
    const canCompleteLearning = computed(() => {
      return (
        currentPhase.value === 'learning' &&
        !phaseIsRunning.value &&
        !learningLoading.value &&
        learningCards.value.length === 0
      );
    });
    const currentLearningCard = computed(() => learningCards.value[learningIndex.value] ?? null);
    const finalizeDisabled = computed(() => {
      if (finalizing.value) return true;
      if (finalizeMode.value === 'reuse') {
        return !selectedGroupId.value;
      }
      return newGroupTitle.value.trim().length === 0;
    });

    async function composeAnswer() {
      if (!session.value || !lastEval.value || phaseIsRunning.value) return;
      composing.value = true;
      try {
        const task = await sessionStore.composeAnswer(session.value.id);
        const summary = task.result_summary as Record<string, string>;
        answerTitle.value = summary?.title ?? question.value?.title ?? '';
        answerText.value = summary?.text ?? draft.value;
        await openFinalize(true);
      } finally {
        composing.value = false;
      }
    }

    async function openFinalize(preserveAnswer = false) {
      if (sessionCompleted.value || phaseIsRunning.value) return;
      if (question.value && !groupsLoading.value && !answerGroups.value.length) {
        await loadAnswerGroupsForQuestion(question.value.id);
      }
      const compare = lastCompare.value;
      if (compare?.decision === 'new_group') {
        finalizeMode.value = 'new';
        selectedGroupId.value = null;
        newGroupTitle.value = question.value?.title ?? '新答案组';
      } else if (compare?.decision === 'reuse' && compare.matchedGroupId) {
        const exists = answerGroups.value.find((group) => group.id === compare.matchedGroupId);
        finalizeMode.value = 'reuse';
        if (exists) {
          selectedGroupId.value = compare.matchedGroupId;
          newGroupTitle.value = '';
        } else if (answerGroups.value.length) {
          selectedGroupId.value = answerGroups.value[0].id;
          newGroupTitle.value = '';
        } else {
          finalizeMode.value = 'new';
          selectedGroupId.value = null;
          newGroupTitle.value = newGroupTitle.value || question.value?.title || '新答案组';
        }
      } else if (answerGroups.value.length) {
        finalizeMode.value = 'reuse';
        selectedGroupId.value = answerGroups.value[0].id;
        newGroupTitle.value = '';
      } else {
        finalizeMode.value = 'new';
        selectedGroupId.value = null;
        newGroupTitle.value = newGroupTitle.value || question.value?.title || '新答案组';
      }
      if (!preserveAnswer) {
        answerTitle.value = question.value?.title ?? '';
        answerText.value = draft.value;
      }
      showFinalize.value = true;
    }

    async function finalize() {
      if (!session.value || phaseIsRunning.value) return;
      finalizing.value = true;
      try {
        const payload = {
          answer_title: answerTitle.value || '最终答案',
          answer_text: answerText.value || draft.value,
        } as SessionFinalizePayload;
        if (finalizeMode.value === 'reuse' && selectedGroupId.value) {
          payload.answer_group_id = selectedGroupId.value;
        } else {
          payload.group_title = newGroupTitle.value || question.value?.title || '新答案组';
        }
        await sessionStore.finalizeSession(session.value.id, payload);
        if (question.value) {
          await loadAnswerGroupsForQuestion(question.value.id);
        }
        showFinalize.value = false;
      } finally {
        finalizing.value = false;
        }
    }

    async function markLearningDone() {
      if (!session.value || !canCompleteLearning.value) return;
      await sessionStore.completeLearning(session.value.id);
    }

    function switchFinalizeMode(mode: 'reuse' | 'new') {
      finalizeMode.value = mode;
      if (mode === 'reuse') {
        if (!selectedGroupId.value && answerGroups.value.length) {
          selectedGroupId.value = answerGroups.value[0].id;
        }
      } else {
        newGroupTitle.value = newGroupTitle.value || question.value?.title || '新答案组';
      }
    }

    function resetLearningState() {
      learningCards.value = [];
      learningIndex.value = 0;
      learningError.value = '';
      learningMessage.value = '';
    }

    async function loadLearningCards() {
      if (!session.value?.answer_id || currentPhase.value !== 'learning' || phaseIsRunning.value) {
        resetLearningState();
        return;
      }
      learningLoading.value = true;
      learningError.value = '';
      try {
        const cards = await fetchDueFlashcards({
          mode: 'guided',
          answerId: session.value.answer_id,
          limit: 20,
        });
        learningCards.value = cards;
        learningIndex.value = 0;
        if (cards.length === 0) {
          learningMessage.value = '该答案的抽认卡已学习完成，请点击“标记学习完成”。';
        } else {
          learningMessage.value = '';
        }
      } catch (err) {
        console.error(err);
        learningError.value = '无法加载抽认卡';
      } finally {
        learningLoading.value = false;
      }
    }

    async function handleLearningReview(score: number) {
      const card = currentLearningCard.value;
      if (!card || learningSubmitting.value) return;
      learningSubmitting.value = true;
      learningError.value = '';
      try {
        await reviewFlashcard(card.card.id, score);
        learningMessage.value = '已记录复习结果';
        await loadLearningCards();
      } catch (err) {
        console.error(err);
        learningError.value = '提交复习结果失败';
      } finally {
        learningSubmitting.value = false;
      }
    }

    function renderLearningCard() {
      const card = currentLearningCard.value;
      if (!card) return null;
      if (card.chunk) {
        const chunk = card.chunk;
        const sentence = chunk.sentence;
        return (
          <div class="card-section">
            <h4>记忆块 #{chunk.order_index}</h4>
            <p class="card__text">{chunk.text}</p>
            <p class="card__translation">英文：{chunk.translation_en ?? '—'}</p>
            <p class="card__translation">中文：{chunk.translation_zh ?? '—'}</p>
            {sentence && (
              <p class="card__meta">
                来源句子：{sentence.text}
                {sentence.answer_id && (
                  <>
                    {' · '}
                    <RouterLink to={`/answers/${sentence.answer_id}`}>查看答案</RouterLink>
                  </>
                )}
              </p>
            )}
          </div>
        );
      }
      if (card.sentence) {
        const sentence = card.sentence;
        return (
          <div class="card-section">
            <h4>句子卡片</h4>
            <p class="card__text">{sentence.text}</p>
            <p class="card__translation">英文：{sentence.translation_en ?? '—'}</p>
            <p class="card__translation">中文：{sentence.translation_zh ?? '—'}</p>
            <p class="card__meta">
              段落 #{sentence.paragraph_id} · 难度：{sentence.difficulty ?? '未标注'}
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
      if (card.lexeme) {
        const lexeme = card.lexeme;
        return (
          <div class="card-section">
            <h4>词块卡片</h4>
            <p class="card__text">
              {lexeme.headword} {lexeme.sense_label && <small>({lexeme.sense_label})</small>}
            </p>
            {lexeme.gloss && <p class="card__translation">释义：{lexeme.gloss}</p>}
            {lexeme.translation_zh && <p class="card__translation">中文：{lexeme.translation_zh}</p>}
            {lexeme.translation_en && <p class="card__translation">英文：{lexeme.translation_en}</p>}
          </div>
        );
      }
      return <p>暂不支持的卡片类型。</p>;
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
            {groupsError.value && <p class="error">{groupsError.value}</p>}
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

        {lastCompare.value && (
          <section class="compare-panel">
            <h3>答案组建议</h3>
            <p>
              LLM 判定：
              {lastCompare.value.decision === 'new_group'
                ? '建议创建新的答案组'
                : lastCompare.value.decision === 'reuse'
                ? '复用现有答案组'
                : '未知'}
            </p>
            {lastCompare.value.reason && <p>理由：{lastCompare.value.reason}</p>}
            {lastCompare.value.differences && lastCompare.value.differences.length > 0 && (
              <details>
                <summary>差异详情</summary>
                <ul>
                  {lastCompare.value.differences.map((item, index) => (
                    <li key={`${item}-${index}`}>{item}</li>
                  ))}
                </ul>
              </details>
            )}
            {lastCompare.value.decision === 'reuse' && matchedAnswerGroup.value && (
              <p>推荐复用答案组：{matchedAnswerGroup.value.title}</p>
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
            <button type="button" onClick={() => openFinalize()} disabled={sessionCompleted.value || phaseIsRunning.value}>
              {sessionCompleted.value ? '已完成' : '完成 Session'}
            </button>
            {currentPhase.value === 'learning' && (
              <button
                type="button"
                onClick={markLearningDone}
                disabled={!canCompleteLearning.value}
              >
                标记学习完成
              </button>
            )}
          </div>
        </section>
        {currentPhase.value === 'learning' && (
          <section class="learning-panel">
            <h3>Guided 抽认卡学习</h3>
            {learningError.value && <p class="error">{learningError.value}</p>}
            {learningMessage.value && <p class="hint">{learningMessage.value}</p>}
            {learningLoading.value && <p>抽认卡加载中...</p>}
            {!learningLoading.value && currentLearningCard.value && (
              <article class="flashcard-card">
                <div class="card__status">
                  <span>
                    进度：{learningIndex.value + 1}/{learningCards.value.length}
                  </span>
                  <span>下次复习：{new Date(currentLearningCard.value.card.due_at).toLocaleString()}</span>
                </div>
                {renderLearningCard()}
                <div class="review-actions">
                  {reviewScoreOptions.map((option) => (
                    <button
                      key={option.score}
                      type="button"
                      onClick={() => handleLearningReview(option.score)}
                      disabled={learningSubmitting.value}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </article>
            )}
            {!learningLoading.value && learningCards.value.length === 0 && !learningError.value && (
              <p>暂无到期的抽认卡，若已学习完毕可点击下方“标记学习完成”。</p>
            )}
            <div class="learning-controls">
              <button
                type="button"
                onClick={() => loadLearningCards()}
                disabled={learningLoading.value || phaseIsRunning.value}
              >
                刷新抽认卡
              </button>
            </div>
          </section>
        )}
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
            <div class="finalize-mode">
              <label>
                <input
                  type="radio"
                  value="reuse"
                  checked={finalizeMode.value === 'reuse'}
                  disabled={!answerGroups.value.length}
                  onChange={() => switchFinalizeMode('reuse')}
                />
                复用现有答案组
              </label>
              <label>
                <input
                  type="radio"
                  value="new"
                  checked={finalizeMode.value === 'new'}
                  onChange={() => switchFinalizeMode('new')}
                />
                创建新答案组
              </label>
            </div>
            {finalizeMode.value === 'reuse' ? (
              answerGroups.value.length ? (
                <label>
                  <span>选择答案组</span>
                  <select
                    value={selectedGroupId.value ?? undefined}
                    onChange={(e) => {
                      const value = Number((e.target as HTMLSelectElement).value);
                      selectedGroupId.value = Number.isFinite(value) ? value : null;
                    }}
                  >
                    {answerGroups.value.map((group) => (
                      <option key={group.id} value={group.id}>
                        {group.title}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <p>暂无可复用的答案组，将自动创建新答案组。</p>
              )
            ) : (
              <label>
                <span>新答案组标题</span>
                <input
                  value={newGroupTitle.value}
                  onInput={(e) => (newGroupTitle.value = (e.target as HTMLInputElement).value)}
                  placeholder="请输入新答案组标题"
                />
              </label>
            )}
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
              <button type="button" onClick={finalize} disabled={finalizeDisabled.value}>
                {finalizing.value ? '提交中...' : '确认并生成答案'}
              </button>
            </div>
          </section>
        )}
      </section>
    );
  },
});
    const finalizeMode = ref<'reuse' | 'new'>('reuse');
    const selectedGroupId = ref<number | null>(null);
    const newGroupTitle = ref('');
