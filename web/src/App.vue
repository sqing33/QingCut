<template>
  <div class="app-container">
    <router-view />
    <RadialNav />
  </div>
</template>

<script setup lang="ts">
import RadialNav from '@/components/RadialNav.vue'
</script>

<style scoped>
.app-container {
  min-height: 100vh;
}
</style>
