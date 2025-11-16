import { defineComponent, reactive, watch, computed } from 'vue';
import type { QuestionPayload } from '../types/question';

export default defineComponent({
  name: 'QuestionForm',
  props: {
    modelValue: {
      type: Object as () => QuestionPayload,
      required: true,
    },
  },
  emits: ['save', 'cancel'],
  setup(props, { emit }) {
    const localForm = reactive<QuestionPayload>({ ...props.modelValue });

    watch(
      () => props.modelValue,
      (value) => {
        Object.assign(localForm, value);
      }
    );

    const tagsInput = computed({
      get: () => (localForm.tags ?? []).join(', '),
      set: (value: string) => {
        localForm.tags = value
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean);
      },
    });

    const bindString = (key: keyof QuestionPayload) => ({
      value: (localForm[key] as string) ?? '',
      onInput: (event: Event) => {
        const target = event.target as HTMLInputElement | HTMLTextAreaElement;
        (localForm[key] as string | undefined) = target.value;
      },
    });

    const bindNumber = (key: 'year' | 'month') => ({
      value: localForm[key],
      onInput: (event: Event) => {
        const target = event.target as HTMLInputElement;
        const value = Number(target.value);
        if (!Number.isNaN(value)) {
          localForm[key] = value;
        }
      },
    });

    const bindSelect = (key: keyof QuestionPayload) => ({
      value: localForm[key] as string,
      onChange: (event: Event) => {
        const target = event.target as HTMLSelectElement;
        (localForm[key] as string | undefined) = target.value as any;
      },
    });

    function handleSubmit() {
      emit('save', { ...localForm, tags: localForm.tags ?? [] });
    }

    function handleCancel() {
      emit('cancel');
    }

    return () => (
      <form class="question-form" onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
        <label>
          类型
          <select {...bindSelect('type')} required>
            <option value="T2">T2</option>
            <option value="T3">T3</option>
          </select>
        </label>
        <label>
          来源
          <input {...bindString('source')} required />
        </label>
        <label>
          年份
          <input type="number" {...bindNumber('year')} required />
        </label>
        <label>
          月份
          <input type="number" min="1" max="12" {...bindNumber('month')} required />
        </label>
        <label>
          套题
          <input {...bindString('suite')} />
        </label>
        <label>
          题号
          <input {...bindString('number')} />
        </label>
        <label>
          标题
          <input {...bindString('title')} required />
        </label>
        <label>
          题目正文
          <textarea rows={4} {...bindString('body')} required></textarea>
        </label>
        <label>
          标签（以逗号分隔）
          <input
            value={tagsInput.value}
            onInput={(event) => {
              const target = event.target as HTMLInputElement;
              tagsInput.value = target.value;
            }}
            placeholder="如：immigration, famille"
          />
        </label>
        <div class="actions">
          <button type="submit">保存</button>
          <button type="button" onClick={handleCancel}>取消</button>
        </div>
      </form>
    );
  },
});
