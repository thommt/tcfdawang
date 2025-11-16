import { defineComponent, reactive, watch, computed, PropType } from 'vue';
import type { QuestionPayload } from '../types/question';

export default defineComponent({
  name: 'QuestionForm',
  props: {
    modelValue: {
      type: Object as () => QuestionPayload,
      required: true,
    },
    editableFields: {
      type: Array as PropType<(keyof QuestionPayload)[]>,
      default: undefined,
    },
  },
  emits: ['save', 'cancel'],
  setup(props, { emit }) {
    const localForm = reactive<QuestionPayload>({ ...props.modelValue });

    watch(
      () => props.modelValue,
      (value) => {
        Object.assign(localForm, value);
      },
      { deep: true, immediate: true }
    );

    const tagsInput = computed({
      get: () => (localForm.tags ?? []).join(' '),
      set: (value: string) => {
        const stripPunctuation = (text: string) =>
          text.replace(/^[\s,.，。、!！?？;；:："'“”'`<>《》()（）\[\]{}【】]+/, '').replace(
            /[\s,.，。、!！?？;；:："'“”'`<>《》()（）\[\]{}【】]+$/,
            ''
          );
        localForm.tags = value
          .split(/\s+/)
          .map((tag) => stripPunctuation(tag).trim())
          .filter(Boolean);
      },
    });

    const isEditable = (field: keyof QuestionPayload) => !props.editableFields || props.editableFields.includes(field);

    const bindString = (key: keyof QuestionPayload) => ({
      name: key,
      value: (localForm[key] as string) ?? '',
      disabled: !isEditable(key),
      onInput: (event: Event) => {
        const target = event.target as HTMLInputElement | HTMLTextAreaElement;
        (localForm[key] as string | undefined) = target.value;
      },
    });

    const bindNumber = (key: 'year' | 'month') => ({
      name: key,
      value: localForm[key],
      disabled: !isEditable(key),
      onInput: (event: Event) => {
        const target = event.target as HTMLInputElement;
        const value = Number(target.value);
        if (!Number.isNaN(value)) {
          localForm[key] = value;
        }
      },
    });

    const bindSelect = (key: keyof QuestionPayload) => ({
      name: key,
      value: localForm[key] as string,
      disabled: !isEditable(key),
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
          标签（以空格分隔）
          <input
            name="tags"
            value={tagsInput.value}
            disabled={!isEditable('tags')}
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
