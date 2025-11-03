<template>
  <div class="page-container">
    <VideoCapture />
  </div>
</template>

<script setup lang="ts">
import VideoCapture from '@/components/VideoCapture.vue'
</script>

<style scoped lang="scss">
.page-container {
  width: 100%;
  min-height: 100vh;
  background: linear-gradient(135deg, #fef3c7 0%, #bfdbfe 50%, #ddd6fe 100%);
}
</style>
