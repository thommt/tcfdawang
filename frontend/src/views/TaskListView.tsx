import { defineComponent, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { useTaskStore } from '../stores/tasks';

export default defineComponent({
  name: 'TaskListView',
  setup() {
    const taskStore = useTaskStore();

    onMounted(() => {
      taskStore.load();
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
                <th>更新时间</th>
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
                  <td>{new Date(task.updated_at).toLocaleString()}</td>
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
