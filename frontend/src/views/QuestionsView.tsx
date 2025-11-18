import { defineComponent, onMounted, ref, computed, watch } from 'vue';
import { RouterLink } from 'vue-router';
import QuestionForm from '../components/QuestionForm';
import { useQuestionStore } from '../stores/questions';
import { useSessionStore } from '../stores/sessions';
import type { QuestionPayload, Question } from '../types/question';
import { questionToPayload, filterQuestions, paginateQuestions } from '../utils/question';

const createEmptyForm = (): QuestionPayload => ({
  type: 'T2',
  source: '',
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  suite: '',
  number: '',
  title: '',
  body: '',
  tags: [],
});

export default defineComponent({
  name: 'QuestionsView',
  setup() {
    const store = useQuestionStore();
    const sessionStore = useSessionStore();
    const formDialog = ref<HTMLDialogElement | null>(null);
    const fetchDialog = ref<HTMLDialogElement | null>(null);
    const fetchInput = ref('');
    const editingId = ref<number | null>(null);
    const searchKeyword = ref('');
    const selectedTags = ref<string[]>([]);
    const typeFilter = ref<'all' | 'T2' | 'T3'>('all');
    const currentPage = ref(1);
    const pageSizeOptions = [10, 20, 50];
    const pageSize = ref(pageSizeOptions[0]);
    const generatingId = ref<number | null>(null);

    const formModel = ref<QuestionPayload>(createEmptyForm());

    onMounted(() => {
      store.load();
      if (!sessionStore.sessions.length) {
        sessionStore.loadSessions();
      }
    });

    function openCreate() {
      formModel.value = createEmptyForm();
      editingId.value = null;
      formDialog.value?.showModal();
    }

    function edit(question: Question) {
      formModel.value = questionToPayload(question);
      editingId.value = question.id;
      formDialog.value?.showModal();
    }

    function closeForm() {
      formDialog.value?.close();
    }

    async function handleSave(payload: QuestionPayload) {
      if (editingId.value) {
        await store.updateQuestion(editingId.value, {
          title: payload.title,
          tags: payload.tags,
        });
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

    async function importFetched() {
      await store.importFetchResults();
      closeFetch();
    }

    async function generateMetadata(questionId: number) {
      generatingId.value = questionId;
      try {
        await store.generateMetadata(questionId);
      } catch (error) {
        console.error(error);
        alert('调用 LLM 失败，请稍后重试');
      } finally {
        if (generatingId.value === questionId) {
          generatingId.value = null;
        }
      }
    }
    const availableTags = computed(() => {
      const tags = new Set<string>();
      store.items.forEach((item) => {
        (item.tags ?? []).forEach((tag) => tags.add(tag));
      });
      return Array.from(tags).sort();
    });

    const filteredItems = computed(() =>
      filterQuestions(store.items, {
        keyword: searchKeyword.value,
        type: typeFilter.value,
        tags: selectedTags.value,
      })
    );

    const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / pageSize.value)));
    const paginatedItems = computed(() =>
      paginateQuestions(filteredItems.value, currentPage.value, pageSize.value)
    );
    const totalItems = computed(() => filteredItems.value.length);

    const reviewInfoByQuestion = computed(() => {
      const info = new Map<number, { latestNote: string; latestAt: string | null; count: number }>();
      sessionStore.sessions.forEach((session) => {
        const questionId = session.question_id;
        const historyEntries = Array.isArray(session.progress_state?.review_notes_history)
          ? (session.progress_state?.review_notes_history as Array<{ note?: string; saved_at?: string }>)
          : [];
        let entries = historyEntries.filter((entry) => typeof entry.note === 'string' && entry.note.trim().length);
        if (!entries.length && session.progress_state?.review_notes) {
          entries = [
            {
              note: session.progress_state.review_notes as string,
              saved_at: (session.completed_at ?? session.started_at)?.toString(),
            },
          ];
        }
        if (!entries.length) {
          return;
        }
        const current = info.get(questionId) ?? { latestNote: '', latestAt: null, count: 0 };
        entries.forEach((entry) => {
          if (!entry.note) return;
          current.count += 1;
          const savedAt = entry.saved_at ?? '';
          if (!current.latestAt || (savedAt && savedAt > current.latestAt)) {
            current.latestAt = savedAt;
            current.latestNote = entry.note;
          }
        });
        info.set(questionId, current);
      });
      return info;
    });

    function toggleTag(tag: string) {
      if (selectedTags.value.includes(tag)) {
        selectedTags.value = selectedTags.value.filter((t) => t !== tag);
      } else {
        selectedTags.value = [...selectedTags.value, tag];
      }
    }

    function clearFilters() {
      searchKeyword.value = '';
      selectedTags.value = [];
      typeFilter.value = 'all';
    }

    function refresh() {
      store.load();
    }

    watch([searchKeyword, typeFilter, () => selectedTags.value.slice(), pageSize], () => {
      currentPage.value = 1;
    });

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

        <section class="filters">
          <div class="filter-item">
            <label>
              关键字
              <input
                value={searchKeyword.value}
                placeholder="标题/来源/内容"
                onInput={(event) => {
                  searchKeyword.value = (event.target as HTMLInputElement).value;
                }}
              />
            </label>
          </div>
          <div class="filter-item">
            <label>
              类型
              <select
                value={typeFilter.value}
                onChange={(event) => {
                  typeFilter.value = (event.target as HTMLSelectElement).value as 'all' | 'T2' | 'T3';
                }}
              >
                <option value="all">全部</option>
                <option value="T2">T2</option>
                <option value="T3">T3</option>
              </select>
            </label>
          </div>
          <div class="filter-item tags">
            <span>标签筛选</span>
            {availableTags.value.length ? (
              <div class="tag-options">
                {availableTags.value.map((tag) => (
                  <label key={tag}>
                    <input
                      type="checkbox"
                      checked={selectedTags.value.includes(tag)}
                      onChange={() => toggleTag(tag)}
                    />
                    {tag}
                  </label>
                ))}
              </div>
            ) : (
              <span class="muted">暂无标签</span>
            )}
          </div>
          <button class="link" type="button" onClick={clearFilters}>
            清空筛选
          </button>
        </section>

        {store.loading && <div class="info">加载中...</div>}
        {store.error && <div class="error">{store.error}</div>}

        {!store.loading && (
          <table class="question-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>类型</th>
                <th>Slug</th>
                <th>标题</th>
                <th>来源</th>
                <th>日期</th>
                <th>标签</th>
                <th>复习要点</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {paginatedItems.value.length ? (
                paginatedItems.value.map((item) => (
                  <tr key={item.id}>
                    <td>{item.id}</td>
                    <td>{item.type}</td>
                    <td>{item.slug ?? '-'}</td>
                    <td>{item.title}</td>
                    <td>{item.source}</td>
                    <td>
                      {item.year}/{item.month}
                    </td>
                    <td>{item.tags.join(', ')}</td>
                    <td>
                      {(() => {
                        const info = reviewInfoByQuestion.value.get(item.id);
                        if (!info || !info.latestNote) {
                          return '—';
                        }
                        const preview = info.latestNote.slice(0, 40);
                        const suffix = info.latestNote.length > 40 ? '…' : '';
                        const title = info.count > 1 ? `${info.latestNote} (共${info.count}条)` : info.latestNote;
                        return (
                          <span title={title}>
                            {preview}
                            {suffix}
                          </span>
                        );
                      })()}
                    </td>
                    <td>
                      <button onClick={() => edit(item)}>编辑</button>
                      <RouterLink class="link" to={`/questions/${item.id}`}>
                        详情
                      </RouterLink>
                      <button
                        onClick={() => generateMetadata(item.id)}
                        disabled={generatingId.value === item.id}
                      >
                        {generatingId.value === item.id ? '生成中...' : 'LLM生成标题'}
                      </button>
                      <button onClick={() => removeQuestion(item.id)}>删除</button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={9} class="empty">
                    当前筛选条件下没有数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        <div class="pagination">
          <div class="page-info">
            <span>
              共 {totalItems.value} 条记录，每页显示
              <select
                value={pageSize.value}
                onChange={(event) => {
                  pageSize.value = Number((event.target as HTMLSelectElement).value);
                }}
              >
                {pageSizeOptions.map((size) => (
                  <option value={size} key={size}>
                    {size}
                  </option>
                ))}
              </select>
              条
            </span>
          </div>
          <div class="page-actions">
            <span>
              第 {currentPage.value} / {totalPages.value} 页
            </span>
            <button
              disabled={currentPage.value === 1}
              onClick={() => {
                currentPage.value = Math.max(1, currentPage.value - 1);
              }}
            >
              上一页
            </button>
            <button
              disabled={currentPage.value >= totalPages.value}
              onClick={() => {
                currentPage.value = Math.min(totalPages.value, currentPage.value + 1);
              }}
            >
              下一页
            </button>
          </div>
        </div>

        <dialog ref={formDialog}>
          <QuestionForm
            modelValue={formModel.value}
            editableFields={editingId.value ? ['title', 'tags'] : undefined}
            onSave={handleSave}
            onCancel={closeForm}
          />
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
              {store.fetchSummary && (
                <p>
                  共 {store.fetchSummary.count} 条，其中 T2: {store.fetchSummary.t2_count ?? 0} 条，T3:{' '}
                  {store.fetchSummary.t3_count ?? 0} 条
                </p>
              )}
              <ul>
                {store.fetchResults.map((result) => (
                  <li key={result.slug}>
                    <strong>{result.slug}</strong> - {result.title}
                  </li>
                ))}
              </ul>
              <button onClick={importFetched}>导入到题库</button>
            </div>
          )}
        </dialog>
      </section>
    );
  },
});
