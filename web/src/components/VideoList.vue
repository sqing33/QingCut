<template>
  <div class="w-64 shadow-xl border-r border-base-300 flex flex-col h-full">
    <div class="p-4 flex-shrink-0">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-bold">📺 视频列表</h2>
        <button @click="refresh" class="btn btn-xs btn-circle btn-ghost" title="刷新">🔄</button>
      </div>

      <!-- 上传视频按钮（可选） -->
      <label v-if="showUpload" class="btn btn-sm btn-primary w-full mb-4">
        <input type="file" @change="handleUpload" accept="video/*" class="hidden" />
        <span>📁 上传视频</span>
      </label>
    </div>

    <!-- 视频列表 (可滚动区域) -->
    <div class="flex-1 overflow-y-auto px-4 pb-4">
      <div v-if="videos.length === 0" class="text-center py-8 text-base-content/60">
        <div class="text-4xl mb-2">🎬</div>
        <p class="text-xs">暂无视频</p>
      </div>

      <div v-else class="space-y-2">
        <button
          v-for="video in videos"
          :key="video.filename"
          @click="selectVideo(video)"
          :class="[
            'w-full text-left p-3 rounded-lg transition-all',
            selectedVideoFilename === video.filename
              ? 'bg-primary text-primary-content shadow-lg'
              : 'bg-base-200 hover:bg-base-300',
          ]"
        >
          <div class="font-medium truncate text-sm" :title="video.filename">
            {{ video.filename }}
          </div>
          <div class="text-xs opacity-70 mt-1">
            <slot name="video-meta" :video="video">
              {{ formatDate(video.created_at) }}
            </slot>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

interface Video {
  filename: string
  path: string
  created_at: number
}

interface Props {
  selectedVideoFilename?: string
  showUpload?: boolean
}

interface Emits {
  (e: 'video-selected', video: Video): void
  (e: 'video-uploaded', data: any): void
  (e: 'show-message', message: string, type: 'info' | 'success' | 'error'): void
}

const props = withDefaults(defineProps<Props>(), {
  selectedVideoFilename: '',
  showUpload: false,
})

const emit = defineEmits<Emits>()

const videos = ref<Video[]>([])

const formatDate = (timestamp: number) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const loadVideos = async () => {
  try {
    const response = await axios.get('/api/videos')
    videos.value = response.data.videos
  } catch (error) {
    console.error('加载视频列表失败:', error)
    emit('show-message', '加载视频列表失败', 'error')
  }
}

const refresh = () => {
  loadVideos()
}

const selectVideo = (video: Video) => {
  emit('video-selected', video)
}

const handleUpload = async (e: Event) => {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return

  const file = input.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('video', file)

  try {
    emit('show-message', '正在上传视频...', 'info')
    const response = await axios.post('/api/upload-video', formData)

    const data = response.data

    if (data.renamed) {
      emit('show-message', `${data.original_filename} 重复，已更名为 ${data.filename}`, 'info')
    } else {
      emit('show-message', '视频上传成功', 'success')
    }

    await loadVideos()

    // 通知父组件视频已上传
    emit('video-uploaded', data)
  } catch (error) {
    console.error('视频上传失败:', error)
    emit('show-message', '视频上传失败', 'error')
  }

  // 重置 input
  input.value = ''
}

// 暴露方法给父组件
defineExpose({
  loadVideos,
  refresh,
})

onMounted(() => {
  loadVideos()
})
</script>

<style scoped lang="scss">
@use '@/styles/glassmorphism.scss';
</style>
