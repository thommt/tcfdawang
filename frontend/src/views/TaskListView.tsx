import { defineComponent, onMounted, computed } from 'vue';
import { RouterLink } from 'vue-router';
import { useTaskStore } from '../stores/tasks';
import { useSessionStore } from '../stores/sessions';

export default defineComponent({
  name: 'TaskListView',
  setup() {
    const taskStore = useTaskStore();
    const sessionStore = useSessionStore();

    onMounted(() => {
      taskStore.load();
      if (!sessionStore.sessions.length) {
        sessionStore.loadSessions();
      }
    });

    const reviewNotesBySession = computed(() => {
      const map = new Map<number, { latest: string; count: number }>();
      sessionStore.sessions.forEach((session) => {
        if (!session.id) return;
        const historyEntries = Array.isArray(session.progress_state?.review_notes_history)
          ? (session.progress_state?.review_notes_history as Array<{ note?: string }>)
          : [];
        let latestNote = session.progress_state?.review_notes as string | undefined;
        let count = historyEntries.length;
        if (historyEntries.length) {
          const lastEntry = historyEntries[historyEntries.length - 1];
          latestNote = (lastEntry.note as string | undefined) || latestNote;
        }
        if (!latestNote) {
          return;
        }
        if (count === 0) {
          count = 1;
        }
        map.set(session.id, { latest: latestNote, count });
      });
      return map;
    });

    return () => (
      <section class="task-list">
        <header>
          <h2>任务中心</h2>
        </header>
        {taskStore.loading && <p>加载中...</p>}
        {taskStore.error && <p class="error">{taskStore.error}</p>}
        {!taskStore.loading && (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>类型</th>
                <th>状态</th>
                <th>Session</th>
                <th>复习要点</th>
                <th>Answer</th>
                <th>更新时间</th>
                <th>错误</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {taskStore.items.map((task) => (
                <tr key={task.id}>
                  <td>{task.id}</td>
                  <td>{task.type}</td>
                  <td>{task.status}</td>
                  <td>
                    {task.session_id ? <RouterLink to={`/sessions/${task.session_id}`}>{task.session_id}</RouterLink> : '—'}
                  </td>
                  <td>
                    {task.session_id && reviewNotesBySession.value.has(task.session_id) ? (
                      (() => {
                        const info = reviewNotesBySession.value.get(task.session_id)!;
                        const preview = info.latest.slice(0, 40);
                        const suffix = info.latest.length > 40 ? '…' : '';
                        const title = info.count > 1 ? `${info.latest} (共${info.count}条)` : info.latest;
                        return (
                          <span title={title}>
                            {preview}
                            {suffix}
                          </span>
                        );
                      })()
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    {task.answer_id ? <RouterLink to={`/answers/${task.answer_id}`}>{task.answer_id}</RouterLink> : '—'}
                  </td>
                  <td>{new Date(task.updated_at).toLocaleString()}</td>
                  <td>{task.error_message || '—'}</td>
                  <td>
                    {['failed', 'canceled'].includes(task.status) && (
                      <button onClick={() => taskStore.retry(task.id)}>重试</button>
                    )}
                    {task.status === 'pending' && (
                      <button onClick={() => taskStore.cancel(task.id)}>取消</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    );
  },
});
