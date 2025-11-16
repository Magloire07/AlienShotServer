<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header>
      <div class="brand">
        <span class="dot" />
        <strong>AlienShot</strong>
      </div>
      <nav>
        <RouterLink to="/admin">Console</RouterLink>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
    <footer>
      <small>Backend Flask · Frontend Vue 3 + Vite</small>
    </footer>
  </div>
</template>
