import { defineComponent, ref, onMounted } from 'vue';
import { fetchConversations } from '../api/conversations';
import type { LLMConversationLog } from '../types/answer';

export default defineComponent({
  name: 'ConversationsView',
  setup() {
    const conversations = ref<LLMConversationLog[]>([]);
    const loading = ref(false);
    const error = ref('');
    const sessionIdInput = ref('');
    const taskIdInput = ref('');

    async function load() {
      loading.value = true;
      error.value = '';
      try {
        const params: { session_id?: number; task_id?: number } = {};
        const sessionId = Number(sessionIdInput.value);
        const taskId = Number(taskIdInput.value);
        if (!Number.isNaN(sessionId) && sessionId > 0) params.session_id = sessionId;
        if (!Number.isNaN(taskId) && taskId > 0) params.task_id = taskId;
        conversations.value = await fetchConversations(params);
      } catch (err) {
        error.value = '无法加载对话记录';
        console.error(err);
      } finally {
        loading.value = false;
      }
    }

    onMounted(() => {
      load();
    });

    return () => (
      <section class="conversations-view">
        <header>
          <h2>LLM 对话记录</h2>
          <p>展示最近的对话输入与输出，便于排查拆分/翻译等任务。</p>
        </header>
        <div class="filters">
          <label>
            Session ID：
            <input
              type="number"
              min="1"
              value={sessionIdInput.value}
              onInput={(event) => {
                const target = event.target as HTMLInputElement;
                sessionIdInput.value = target.value;
              }}
            />
          </label>
          <label>
            Task ID：
            <input
              type="number"
              min="1"
              value={taskIdInput.value}
              onInput={(event) => {
                const target = event.target as HTMLInputElement;
                taskIdInput.value = target.value;
              }}
            />
          </label>
          <button type="button" onClick={load} disabled={loading.value}>
            {loading.value ? '加载中...' : '刷新'}
          </button>
        </div>
        {error.value && <p class="error">{error.value}</p>}
        {!loading.value && conversations.value.length === 0 && <p>暂无记录。</p>}
        <ul class="conversation-list">
          {conversations.value.map((item) => (
            <li key={item.id} class="conversation-item">
              <div class="conversation-meta">
                <strong>#{item.id}</strong> · {item.purpose} · {new Date(item.created_at).toLocaleString()}
              </div>
              <details>
                <summary>查看详情</summary>
                <pre>messages: {JSON.stringify(item.messages, null, 2)}</pre>
                <pre>result: {JSON.stringify(item.result, null, 2)}</pre>
              </details>
            </li>
          ))}
        </ul>
      </section>
    );
  }
});
