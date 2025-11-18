<template>
  <section>
    <h2>欢迎来到 TCF 大王</h2>
    <p>根据 spec.md 与 frontend_spec.md，我们将在这里构建题目管理、学习工作台等页面。</p>
    <router-link to="/flashcards">前往抽认卡训练</router-link>
    <br>
    <router-link to="/llm-conversations">查看 LLM 对话记录</router-link>
  </section>
</template>

<script setup lang="ts">
</script>

<style scoped>
section {
  padding: 2rem;
  background: #f7fafc;
  border-radius: 0.5rem;
}
</style>
