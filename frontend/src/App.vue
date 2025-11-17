<template>
  <div class="app-shell">
    <header class="app-header">
      <h1>TCF 大王</h1>
      <nav>
        <RouterLink to="/questions">题库</RouterLink>
        <RouterLink to="/tasks">任务</RouterLink>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: #1f2933;
  color: #fff;
  padding: 1rem;
}

main {
  flex: 1;
  padding: 1rem;
}
</style>
