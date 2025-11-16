import { defineComponent, onMounted, reactive, ref } from 'vue';
import QuestionForm from '../components/QuestionForm';
import { useQuestionStore } from '../stores/questions';
import type { QuestionPayload, Question } from '../types/question';

export default defineComponent({
  name: 'QuestionsView',
  setup() {
    const store = useQuestionStore();
    const formDialog = ref<HTMLDialogElement | null>(null);
    const fetchDialog = ref<HTMLDialogElement | null>(null);
    const fetchInput = ref('');
    const editingId = ref<number | null>(null);

    const emptyForm: QuestionPayload = {
      type: 'T2',
      source: '',
      year: new Date().getFullYear(),
      month: new Date().getMonth() + 1,
      suite: '',
      number: '',
      title: '',
      body: '',
      tags: [],
    };

    const formModel = reactive<QuestionPayload>({ ...emptyForm });

    onMounted(() => {
      store.load();
    });

    function openCreate() {
      Object.assign(formModel, emptyForm);
      editingId.value = null;
      formDialog.value?.showModal();
    }

    function edit(question: Question) {
      Object.assign(formModel, { ...question });
      editingId.value = question.id;
      formDialog.value?.showModal();
    }

    function closeForm() {
      formDialog.value?.close();
    }

    async function handleSave(payload: QuestionPayload) {
      if (editingId.value) {
        await store.updateQuestion(editingId.value, payload);
      } else {
        await store.addQuestion(payload);
      }
      closeForm();
    }

    async function removeQuestion(id: number) {
      if (confirm('确认删除该题目？')) {
        await store.removeQuestion(id);
      }
    }

    function openFetch() {
      fetchDialog.value?.showModal();
    }

    function closeFetch() {
      fetchDialog.value?.close();
    }

    async function runFetch() {
      const urls = fetchInput.value
        .split('\n')
        .map((u) => u.trim())
        .filter(Boolean);
      if (!urls.length) return;
      await store.runFetch(urls);
    }

    function refresh() {
      store.load();
    }

    return () => (
      <section class="questions-view">
        <header class="toolbar">
          <h2>题目管理</h2>
          <div class="actions">
            <button onClick={openCreate}>新增题目</button>
            <button onClick={refresh}>刷新</button>
            <button onClick={openFetch}>抓取题目</button>
          </div>
        </header>

        {store.loading && <div class="info">加载中...</div>}
        {store.error && <div class="error">{store.error}</div>}

        {!store.loading && (
          <table class="question-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>类型</th>
                <th>标题</th>
                <th>来源</th>
                <th>日期</th>
                <th>标签</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {store.items.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.type}</td>
                  <td>{item.title}</td>
                  <td>{item.source}</td>
                  <td>
                    {item.year}/{item.month}
                  </td>
                  <td>{item.tags.join(', ')}</td>
                  <td>
                    <button onClick={() => edit(item)}>编辑</button>
                    <button onClick={() => removeQuestion(item.id)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <dialog ref={formDialog}>
          <QuestionForm modelValue={formModel} onSave={handleSave} onCancel={closeForm} />
        </dialog>

        <dialog ref={fetchDialog}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              runFetch();
            }}
          >
            <h3>抓取题目</h3>
            <label>URL 列表（每行一个）</label>
            <textarea
              rows={4}
              value={fetchInput.value}
              placeholder="https://example.com/page"
              onInput={(event) => {
                fetchInput.value = (event.target as HTMLTextAreaElement).value;
              }}
            ></textarea>
            <div class="actions">
              <button type="submit">抓取</button>
              <button type="button" onClick={closeFetch}>
                关闭
              </button>
            </div>
          </form>
          {store.fetchResults.length > 0 && (
            <div>
              <h4>抓取结果</h4>
              <ul>
                {store.fetchResults.map((result) => (
                  <li key={result.slug}>
                    <strong>{result.slug}</strong> - {result.title}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </dialog>
      </section>
    );
  },
});
