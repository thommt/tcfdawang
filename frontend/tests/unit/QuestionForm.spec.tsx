import { mount } from '@vue/test-utils';
import { describe, it, expect } from 'vitest';
import QuestionForm from '../../src/components/QuestionForm';
import type { QuestionPayload } from '../../src/types/question';

const buildPayload = (): QuestionPayload => ({
  type: 'T2',
  source: 'alpha',
  year: 2024,
  month: 10,
  suite: 'A',
  number: '01',
  title: 'Sample title',
  body: 'Sample body',
  tags: ['immigration'],
});

describe('QuestionForm', () => {
  it('displays incoming data when editing', async () => {
    const wrapper = mount(QuestionForm, {
      props: {
        modelValue: buildPayload(),
      },
    });
    const source = wrapper.find('input[name="source"]');
    expect((source.element as HTMLInputElement).value).toBe('alpha');

    const updatedPayload = { ...buildPayload(), source: 'beta', title: 'Updated' };
    await wrapper.setProps({ modelValue: updatedPayload });

    expect((wrapper.find('input[name="source"]').element as HTMLInputElement).value).toBe('beta');
    expect((wrapper.find('input[name="title"]').element as HTMLInputElement).value).toBe('Updated');
  });

  it('disables non-editable fields', () => {
    const wrapper = mount(QuestionForm, {
      props: {
        modelValue: buildPayload(),
        editableFields: ['title', 'tags'],
      },
    });
    expect((wrapper.find('input[name="source"]').element as HTMLInputElement).disabled).toBe(true);
    expect((wrapper.find('input[name="title"]').element as HTMLInputElement).disabled).toBe(false);
  });

  it('splits tags by spaces and strips punctuation', async () => {
    const wrapper = mount(QuestionForm, {
      props: {
        modelValue: buildPayload(),
      },
    });
    const tagsInput = wrapper.find('input[name="tags"]');
    await tagsInput.setValue('  教育，，  城市? 家庭！ ');
    await wrapper.find('form').trigger('submit.prevent');
    const emitted = wrapper.emitted('save');
    expect(emitted).toBeTruthy();
    const payload = emitted?.[0]?.[0] as QuestionPayload;
    expect(payload.tags).toEqual(['教育', '城市', '家庭']);
  });
});
