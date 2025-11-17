import { defineComponent, ref, onMounted, watch, computed } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { useSessionStore } from '../stores/sessions';
import { useQuestionStore } from '../stores/questions';
import type { Session } from '../types/session';
import { fetchQuestionById } from '../api/questions';
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

    const showFinalize = ref(false);
    const answerTitle = ref('');
    const answerText = ref('');

    const sessionCompleted = computed(() => session.value?.status === 'completed');

    const session = computed<Session | null>(() => sessionStore.currentSession);
    const lastEval = computed(() => {
      const evalData = session.value?.progress_state?.last_eval as Record<string, unknown> | undefined;
      if (!evalData) return null;
      return {
        feedback: evalData.feedback as string | undefined,
        score: evalData.score as number | undefined,
      };
    });

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
      }
    }

    watch(
      () => sessionStore.currentSession,
      (value) => {
        if (value) {
          draft.value = value.user_answer_draft ?? '';
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

        <section class="workspace">
          <label>
            <span>草稿</span>
            <textarea
              rows={8}
              value={draft.value}
              onInput={(event) => {
                draft.value = (event.target as HTMLTextAreaElement).value;
              }}
              placeholder="在此输入你的答案草稿"
            ></textarea>
          </label>
          <div class="actions">
            <button onClick={saveDraft} disabled={saving.value || sessionCompleted.value}>
              {saving.value ? '保存中...' : '保存草稿'}
            </button>
            <button onClick={evaluate} disabled={evalRunning.value || sessionCompleted.value}>
              {evalRunning.value ? '评估中...' : '请求评估'}
            </button>
            <button onClick={composeAnswer} disabled={composing.value || sessionCompleted.value}>
              {composing.value ? '生成中...' : 'LLM 生成答案'}
            </button>
            <button type="button" onClick={openFinalize} disabled={sessionCompleted.value}>
              {sessionCompleted.value ? '已完成' : '完成 Session'}
            </button>
          </div>
        </section>

        <section class="eval-panel">
          <h3>最近评估</h3>
          {lastEval.value ? (
            <div class="feedback-card">
              <p>{lastEval.value.feedback}</p>
              <p>评分：{lastEval.value.score ?? '未提供'}</p>
            </div>
          ) : (
            <p>尚未进行评估。</p>
          )}
        </section>
        {lastCompose.value && (
          <section class="compose-panel">
            <h3>LLM 生成的答案</h3>
            <article>
              <strong>{(lastCompose.value as Record<string, unknown>).title as string}</strong>
              <p>{(lastCompose.value as Record<string, unknown>).text as string}</p>
            </article>
          </section>
        )}
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
