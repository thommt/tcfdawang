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
    const question = ref<Question | null>(null);

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
            <button onClick={saveDraft} disabled={saving.value}>
              {saving.value ? '保存中...' : '保存草稿'}
            </button>
            <button onClick={evaluate} disabled={evalRunning.value}>
              {evalRunning.value ? '评估中...' : '请求评估'}
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
      </section>
    );
  },
});
