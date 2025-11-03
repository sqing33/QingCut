<template>
  <div class="min-h-screen flex">
    <!-- 左侧面板：视频列表 + 类名管理 -->
    <div class="w-64 glass-panel shadow-xl border-r border-base-300 flex flex-col h-screen">
      <!-- 视频列表区域 (1/2) -->
      <div class="flex-1 border-b border-base-300 flex flex-col min-h-0">
        <VideoList
          :selected-video-filename="currentVideoFilename"
          :show-upload="true"
          @video-selected="onVideoSelected"
          @video-uploaded="onVideoUploaded"
          @show-message="showMessage"
        />
      </div>

      <!-- 类名管理区域 (1/3) -->
      <div class="flex-1 glass-panel-light flex flex-col min-h-0">
        <div class="p-4 flex-shrink-0">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-bold">🏷️ 类名管理</h2>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto px-4 pb-4">
          <ClassGroupManager
            :selected-class-id="selectedClassId"
            @select-class="onSelectClass"
            @group-changed="onGroupChanged"
            @show-message="showMessage"
            @class-added="onClassAdded"
          />
        </div>
      </div>
    </div>

    <!-- 中间视频播放区域 -->
    <div class="flex-1 flex flex-col p-4 overflow-hidden">
      <!-- 视频显示区域 -->
      <div
        class="flex-1 glass-panel rounded-2xl shadow-xl overflow-hidden relative flex items-center justify-center mb-4"
        ref="videoWrapper"
      >
        <!-- 空状态占位 -->
        <div v-if="!videoUrl" class="text-center">
          <div class="text-8xl mb-4 opacity-30">🎬</div>
          <div class="text-2xl font-semibold text-base-content/40 tracking-wide">
            从左侧选择视频开始
          </div>
        </div>

        <!-- 视频元素 -->
        <video
          v-show="videoUrl"
          ref="videoRef"
          @loadedmetadata="onVideoLoaded"
          crossorigin="anonymous"
          class="video-element"
        >
          <source v-if="videoUrl" :src="videoUrl" type="video/mp4" />
        </video>

        <!-- Canvas 叠加层 -->
        <canvas
          ref="canvasRef"
          class="overlay-canvas"
          @mousedown="onMouseDown"
          @mousemove="onMouseMove"
          @mouseup="onMouseUp"
          @mouseleave="onMouseLeave"
          v-show="isSelectionMode"
        ></canvas>

        <!-- 标注工具栏（框选模式下显示） -->
        <div
          v-if="isSelectionMode && selectionRect"
          class="absolute top-4 right-4 bg-base-100 shadow-2xl rounded-lg p-3 border border-base-300 z-10"
        >
          <div class="flex flex-col gap-2">
            <!-- 类名选择 -->
            <div class="flex items-center gap-2">
              <label class="text-xs font-semibold whitespace-nowrap">类名:</label>
              <select
                v-model="selectedClassId"
                @change="onClassChange"
                class="select select-bordered select-xs w-32"
                :class="{ 'select-error': !selectedClassId }"
              >
                <option :value="null" disabled>请选择类名</option>
                <option v-for="cls in displayedClasses" :key="cls.id" :value="cls.id">
                  {{ cls.name }}
                </option>
              </select>
            </div>

            <!-- 操作按钮 -->
            <div class="flex gap-2">
              <button
                v-if="!isEditingAnnotation"
                @click="addAnnotation"
                class="btn btn-xs btn-success flex-1"
                :disabled="!selectedClassId"
              >
                ➕ 添加标注
              </button>
              <button
                v-if="isEditingAnnotation"
                @click="finishEditAnnotation"
                class="btn btn-xs btn-primary flex-1"
              >
                ✓ 完成编辑
              </button>
              <button
                v-if="isEditingAnnotation"
                @click="deleteEditingAnnotation"
                class="btn btn-xs btn-error"
              >
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 视频控制栏 -->
      <div class="card glass-panel shadow-xl p-4">
        <!-- 进度条 -->
        <div v-if="videoUrl" class="mb-4 pb-4 border-b border-base-300">
          <input
            type="range"
            class="range range-accent range-xs w-full"
            :value="currentTime"
            :max="duration"
            @input="seekVideo"
            step="0.1"
          />
          <div class="flex justify-between text-xs text-base-content/60 font-medium mt-1">
            <span>{{ formatTime(currentTime) }}</span>
            <span>{{ formatTime(duration) }}</span>
          </div>
        </div>

        <!-- 控制按钮 -->
        <div class="relative flex flex-wrap gap-3 items-center justify-between">
          <!-- 左侧操作按钮 -->
          <div class="flex gap-2 flex-wrap">
            <button
              @click="toggleSelectionMode"
              class="btn btn-sm btn-warning gap-2"
              :disabled="!videoUrl"
            >
              <span>✂️</span>
              <span class="hidden sm:inline">{{ isSelectionMode ? '退出框选' : '开启框选' }}</span>
            </button>
            <button
              v-if="isSelectionMode && currentAnnotations.length > 0"
              @click="saveAllAnnotations"
              class="btn btn-sm btn-primary gap-2"
            >
              <span>💾</span>
              <span class="hidden sm:inline">保存标注({{ currentAnnotations.length }})</span>
            </button>
          </div>

          <!-- 中间播放控制 -->
          <div
            v-if="videoUrl"
            class="absolute left-1/2 transform -translate-x-1/2 flex gap-2 items-center"
          >
            <button @click="skipBackward" class="btn btn-sm btn-circle" :disabled="!videoUrl">
              ⏪
            </button>
            <button @click="togglePlay" class="btn btn-success btn-circle" :disabled="!videoUrl">
              {{ isPlaying ? '⏸️' : '▶️' }}
            </button>
            <button @click="skipForward" class="btn btn-sm btn-circle" :disabled="!videoUrl">
              ⏩
            </button>
            <!-- 播放速度选择 -->
            <div v-if="videoUrl" class="flex items-center gap-2">
              <label class="text-xs font-semibold text-base-content/60 whitespace-nowrap"
                >速度</label
              >
              <select
                v-model="playbackSpeed"
                @change="changePlaybackSpeed"
                class="select select-bordered select-xs focus:outline-none"
              >
                <option value="0.25">0.25x</option>
                <option value="0.5">0.5x</option>
                <option value="0.75">0.75x</option>
                <option value="1">1x</option>
                <option value="1.25">1.25x</option>
                <option value="1.5">1.5x</option>
                <option value="2">2x</option>
              </select>
            </div>
          </div>

          <!-- 右侧键盘提示 -->
          <div class="hidden lg:flex gap-2 text-xs">
            <div class="flex items-center gap-1">
              <kbd class="kbd kbd-xs">R</kbd>
              <span class="text-base-content/60">进入框选</span>
            </div>
            <div class="flex items-center gap-1">
              <kbd class="kbd kbd-xs">Esc</kbd>
              <span class="text-base-content/60">退出框选</span>
            </div>
            <div class="flex items-center gap-1">
              <kbd class="kbd kbd-xs">Enter</kbd>
              <span class="text-base-content/60">添加/完成</span>
            </div>
            <div class="flex items-center gap-1">
              <kbd class="kbd kbd-xs">Del</kbd>
              <span class="text-base-content/60">删除</span>
            </div>
            <div class="flex items-center gap-1">
              <kbd class="kbd kbd-xs">N</kbd>
              <span class="text-base-content/60">保存</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧截图列表 -->
    <div class="w-80 glass-panel shadow-xl border-l border-base-300 flex flex-col h-screen">
      <div class="p-4 flex-shrink-0">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-bold">
            🖼️ 截图列表
            <span class="badge badge-primary ml-2">{{ currentFrames.length }}</span>
          </h2>
          <button @click="loadFrames" class="btn btn-xs btn-circle btn-ghost" title="刷新">
            🔄
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto px-4 pb-4">
        <div v-if="!currentVideoFilename" class="text-center py-8 text-base-content/60">
          <div class="text-4xl mb-2">🖼️</div>
          <p class="text-xs">请先选择视频</p>
        </div>

        <div v-else-if="currentFrames.length === 0" class="text-center py-8 text-base-content/60">
          <div class="text-4xl mb-2">📷</div>
          <p class="text-xs">暂无截图</p>
          <p class="text-xs mt-1">开始截取帧</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="frame in currentFrames"
            :key="frame.filename"
            class="card bg-base-200 shadow hover:shadow-lg transition-all cursor-pointer"
            @click="previewFrame(frame)"
          >
            <figure class="h-32 bg-base-300">
              <img
                :src="`${API_BASE_URL}${frame.path}`"
                :alt="frame.filename"
                class="w-full h-full object-cover"
              />
            </figure>
            <div class="card-body p-2">
              <div class="text-xs truncate" :title="frame.filename">
                {{ frame.filename }}
              </div>
              <div class="text-xs text-base-content/60">
                {{ formatDate(frame.created_at) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 状态提示 -->
    <div v-if="message" class="toast toast-top toast-center">
      <div
        :class="[
          'alert',
          messageType === 'alert-success'
            ? 'alert-success'
            : messageType === 'alert-error'
              ? 'alert-error'
              : 'alert-info',
        ]"
      >
        <span>{{ message }}</span>
      </div>
    </div>

    <!-- 图片预览模态框 -->
    <div v-if="showPreview" class="modal modal-open" @click.self="closePreview">
      <div class="modal-box max-w-4xl p-0 overflow-hidden">
        <div class="relative">
          <button
            @click="closePreview"
            class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2 z-10 bg-base-100"
          >
            ✕
          </button>
          <canvas ref="previewCanvasRef" class="w-full"></canvas>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { API_BASE_URL } from '@/config'
import ClassGroupManager from './ClassGroupManager.vue'
import VideoList from './VideoList.vue'

interface Video {
  filename: string
  path: string
  created_at: number
}

interface Frame {
  filename: string
  path: string
  created_at: number
  video_filename?: string
}

interface Class {
  id: number
  name: string
  color: string
  order?: number
}

const videoRef = ref<HTMLVideoElement>()
const canvasRef = ref<HTMLCanvasElement>()
const videoWrapper = ref<HTMLDivElement>()
const previewCanvasRef = ref<HTMLCanvasElement>()

const isPlaying = ref(false)
const isSelectionMode = ref(false)
const videoUrl = ref('')
const currentVideoFilename = ref('')
const message = ref('')
const messageType = ref('alert-info')
const allFrames = ref<Frame[]>([])
const currentTime = ref(0)
const duration = ref(0)
const playbackSpeed = ref('1')

const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const dragEnd = ref({ x: 0, y: 0 })
const selectionRect = ref<{ x: number; y: number; width: number; height: number } | null>(null)
const isResizing = ref(false)
const resizeHandle = ref<string>('')
const resizeStartRect = ref<{ x: number; y: number; width: number; height: number } | null>(null)

// 多标注支持：存储当前帧的所有标注
interface Annotation {
  box: { x: number; y: number; width: number; height: number }
  classId: number
  className: string
  color: string
}
const currentAnnotations = ref<Annotation[]>([])

// 已保存标注框的编辑状态
const editingAnnotationIndex = ref<number | null>(null)
const isEditingAnnotation = ref(false)

// 类名管理状态
const allClasses = ref<Class[]>([])
const globalClasses = ref<Class[]>([])
const selectedClassId = ref<number | null>(null)

// 从ClassGroupManager接收的当前类名列表
const groupClasses = ref<Class[]>([])

const OUTPUT_SIZE = 640
const SKIP_SECONDS = 5
const LETTERBOX_COLOR = 'rgb(114, 114, 114)'

const displayedClasses = computed(() => {
  // 优先使用从ClassGroupManager传递过来的类名列表
  if (groupClasses.value.length > 0) {
    return groupClasses.value
  }
  // 如果没有选中组，使用全局类名作为后备
  return globalClasses.value
})

const currentFrames = computed(() => {
  if (!currentVideoFilename.value) return []
  return allFrames.value.filter((frame) => frame.video_filename === currentVideoFilename.value)
})

const loadFrames = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/frames`)
    if (!response.ok) throw new Error('获取截图列表失败')
    const data = await response.json()
    allFrames.value = data.frames
  } catch (error) {
    console.error('加载截图列表失败:', error)
    showMessage('加载截图列表失败', 'error')
  }
}

const onVideoSelected = (video: Video) => {
  if (videoRef.value) {
    videoRef.value.pause()
    isPlaying.value = false
  }

  currentVideoFilename.value = video.filename
  videoUrl.value = `${API_BASE_URL}${video.path}`

  setTimeout(() => {
    if (videoRef.value) {
      videoRef.value.load()
      // 视频默认暂停，不自动播放
      isPlaying.value = false
    }
  }, 100)

  showMessage(`已选择: ${video.filename}`, 'success')
}

const onVideoUploaded = (data: any) => {
  // 自动选择上传的视频
  onVideoSelected({
    filename: data.filename,
    path: `/uploads/videos/${data.filename}`,
    created_at: Date.now() / 1000,
  })
}

watch(currentVideoFilename, () => {
  loadFrames()
})

const formatDate = (timestamp: number) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const updateTime = () => {
  if (videoRef.value) {
    currentTime.value = videoRef.value.currentTime
    duration.value = videoRef.value.duration || 0
  }
}

const seekVideo = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (videoRef.value) {
    videoRef.value.currentTime = parseFloat(target.value)
  }
}

const skipForward = () => {
  if (videoRef.value) {
    videoRef.value.currentTime = Math.min(
      videoRef.value.currentTime + SKIP_SECONDS,
      videoRef.value.duration,
    )
  }
}

const skipBackward = () => {
  if (videoRef.value) {
    videoRef.value.currentTime = Math.max(videoRef.value.currentTime - SKIP_SECONDS, 0)
  }
}

const changePlaybackSpeed = () => {
  if (videoRef.value) {
    videoRef.value.playbackRate = parseFloat(playbackSpeed.value)
  }
}

const formatTime = (seconds: number) => {
  if (isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const handleKeyPress = (e: KeyboardEvent) => {
  if (e.key === ' ') {
    e.preventDefault()
    if (videoUrl.value) togglePlay()
  } else if ((e.key === 'r' || e.key === 'R') && videoUrl.value && !isSelectionMode.value) {
    e.preventDefault()
    enterSelectionMode()
  } else if (e.key === 'Enter' && isSelectionMode.value && selectionRect.value) {
    e.preventDefault()
    if (isEditingAnnotation.value) {
      finishEditAnnotation()
    } else {
      addAnnotation()
    }
  } else if (
    (e.key === 'Delete' || e.key === 'Backspace') &&
    isSelectionMode.value &&
    isEditingAnnotation.value
  ) {
    e.preventDefault()
    deleteEditingAnnotation()
  } else if (
    (e.key === 'n' || e.key === 'N') &&
    isSelectionMode.value &&
    currentAnnotations.value.length > 0
  ) {
    e.preventDefault()
    saveAllAnnotations()
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault()
    if (videoUrl.value) skipBackward()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    if (videoUrl.value) skipForward()
  } else if (e.key === 'Escape' && isSelectionMode.value) {
    exitSelectionMode()
  }
}

onMounted(() => {
  loadFrames()
  loadClasses()

  if (videoRef.value) {
    videoRef.value.addEventListener('timeupdate', updateTime)
    videoRef.value.addEventListener('loadedmetadata', () => {
      duration.value = videoRef.value?.duration || 0
    })
  }

  window.addEventListener('keydown', handleKeyPress)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress)
})

const showMessage = (msg: string, type: 'info' | 'success' | 'error' = 'info') => {
  message.value = msg
  messageType.value = `alert-${type}`
  setTimeout(() => {
    message.value = ''
  }, 3000)
}

const togglePlay = () => {
  if (!videoRef.value) return

  if (isPlaying.value) {
    videoRef.value.pause()
  } else {
    videoRef.value.play()
  }
  isPlaying.value = !isPlaying.value
}

const enterSelectionMode = () => {
  isSelectionMode.value = true
  videoRef.value?.pause()
  isPlaying.value = false
  setupCanvas()

  // 清空之前的标注
  currentAnnotations.value = []

  showMessage('框选区域并添加标注，完成后点击保存', 'info')
}

const exitSelectionMode = () => {
  isSelectionMode.value = false
  isDragging.value = false
  selectionRect.value = null
  currentAnnotations.value = []
  showMessage('已退出框选模式', 'info')
}

const toggleSelectionMode = () => {
  if (isSelectionMode.value) {
    exitSelectionMode()
  } else {
    enterSelectionMode()
  }
}

const setupCanvas = () => {
  if (!canvasRef.value || !videoRef.value || !videoWrapper.value) return

  const videoWidth = videoRef.value.videoWidth
  const videoHeight = videoRef.value.videoHeight

  const containerRect = videoWrapper.value.getBoundingClientRect()
  const containerWidth = containerRect.width
  const containerHeight = containerRect.height

  const videoAspect = videoWidth / videoHeight
  const containerAspect = containerWidth / containerHeight

  let displayWidth, displayHeight
  if (containerAspect > videoAspect) {
    displayHeight = containerHeight
    displayWidth = displayHeight * videoAspect
  } else {
    displayWidth = containerWidth
    displayHeight = displayWidth / videoAspect
  }

  canvasRef.value.width = videoWidth
  canvasRef.value.height = videoHeight

  canvasRef.value.style.width = `${displayWidth}px`
  canvasRef.value.style.height = `${displayHeight}px`
}

const getCanvasCoords = (e: MouseEvent) => {
  if (!canvasRef.value) return { x: 0, y: 0 }
  const rect = canvasRef.value.getBoundingClientRect()
  const scaleX = canvasRef.value.width / rect.width
  const scaleY = canvasRef.value.height / rect.height
  return {
    x: (e.clientX - rect.left) * scaleX,
    y: (e.clientY - rect.top) * scaleY,
  }
}

const getResizeHandle = (
  x: number,
  y: number,
  rect: { x: number; y: number; width: number; height: number },
): string => {
  const threshold = 8

  if (Math.abs(x - rect.x) < threshold && Math.abs(y - rect.y) < threshold) return 'nw'
  if (Math.abs(x - (rect.x + rect.width)) < threshold && Math.abs(y - rect.y) < threshold)
    return 'ne'
  if (Math.abs(x - rect.x) < threshold && Math.abs(y - (rect.y + rect.height)) < threshold)
    return 'sw'
  if (
    Math.abs(x - (rect.x + rect.width)) < threshold &&
    Math.abs(y - (rect.y + rect.height)) < threshold
  )
    return 'se'

  if (Math.abs(x - rect.x) < threshold && y > rect.y && y < rect.y + rect.height) return 'w'
  if (Math.abs(x - (rect.x + rect.width)) < threshold && y > rect.y && y < rect.y + rect.height)
    return 'e'
  if (Math.abs(y - rect.y) < threshold && x > rect.x && x < rect.x + rect.width) return 'n'
  if (Math.abs(y - (rect.y + rect.height)) < threshold && x > rect.x && x < rect.x + rect.width)
    return 's'

  return ''
}

// 检查点是否在标注框的边界上
const getAnnotationOnBorder = (x: number, y: number): number => {
  const threshold = 5
  for (let i = currentAnnotations.value.length - 1; i >= 0; i--) {
    const box = currentAnnotations.value[i].box
    // 检查是否在框的边界上
    const onLeft =
      Math.abs(x - box.x) < threshold &&
      y >= box.y - threshold &&
      y <= box.y + box.height + threshold
    const onRight =
      Math.abs(x - (box.x + box.width)) < threshold &&
      y >= box.y - threshold &&
      y <= box.y + box.height + threshold
    const onTop =
      Math.abs(y - box.y) < threshold &&
      x >= box.x - threshold &&
      x <= box.x + box.width + threshold
    const onBottom =
      Math.abs(y - (box.y + box.height)) < threshold &&
      x >= box.x - threshold &&
      x <= box.x + box.width + threshold

    if (onLeft || onRight || onTop || onBottom) {
      return i
    }
  }
  return -1
}

const onMouseDown = (e: MouseEvent) => {
  if (!isSelectionMode.value) return

  const coords = getCanvasCoords(e)

  // 优先检查是否点击了当前选区的调整手柄
  if (selectionRect.value) {
    const handle = getResizeHandle(coords.x, coords.y, selectionRect.value)
    if (handle) {
      isResizing.value = true
      // 保持编辑状态，不要改变 isEditingAnnotation
      resizeHandle.value = handle
      resizeStartRect.value = { ...selectionRect.value }
      dragStart.value = coords
      return
    }
  }

  // 检查是否点击了已保存标注框的边界
  const annotationIndex = getAnnotationOnBorder(coords.x, coords.y)
  if (annotationIndex !== -1) {
    // 进入编辑模式
    editingAnnotationIndex.value = annotationIndex
    isEditingAnnotation.value = true
    const annotation = currentAnnotations.value[annotationIndex]
    selectionRect.value = { ...annotation.box }
    selectedClassId.value = annotation.classId

    // 检查是否点击了调整手柄
    const handle = getResizeHandle(coords.x, coords.y, selectionRect.value)
    if (handle) {
      isResizing.value = true
      resizeHandle.value = handle
      resizeStartRect.value = { ...selectionRect.value }
      dragStart.value = coords
    }
    drawSelection()
    return
  }

  // 开始新的框选
  isDragging.value = true
  dragStart.value = coords
  dragEnd.value = coords
  selectionRect.value = null
  editingAnnotationIndex.value = null
  isEditingAnnotation.value = false
}

const onMouseMove = (e: MouseEvent) => {
  if (!isSelectionMode.value) return

  const coords = getCanvasCoords(e)

  if (!isDragging.value && !isResizing.value && canvasRef.value) {
    // 检查当前选区的调整手柄
    if (selectionRect.value) {
      const handle = getResizeHandle(coords.x, coords.y, selectionRect.value)
      if (handle) {
        const cursors: Record<string, string> = {
          nw: 'nwse-resize',
          ne: 'nesw-resize',
          sw: 'nesw-resize',
          se: 'nwse-resize',
          n: 'ns-resize',
          s: 'ns-resize',
          w: 'ew-resize',
          e: 'ew-resize',
        }
        canvasRef.value.style.cursor = cursors[handle]
        return
      }
    }

    // 检查是否悬停在已保存标注框的边界上
    const annotationIndex = getAnnotationOnBorder(coords.x, coords.y)
    if (annotationIndex !== -1) {
      canvasRef.value.style.cursor = 'pointer'
      return
    }

    canvasRef.value.style.cursor = 'crosshair'
  }

  if (isDragging.value) {
    dragEnd.value = coords
    drawSelection()
  } else if (isResizing.value && resizeStartRect.value) {
    const dx = coords.x - dragStart.value.x
    const dy = coords.y - dragStart.value.y
    const startRect = resizeStartRect.value

    let newRect = { ...startRect }

    switch (resizeHandle.value) {
      case 'nw':
        newRect.x = startRect.x + dx
        newRect.y = startRect.y + dy
        newRect.width = startRect.width - dx
        newRect.height = startRect.height - dy
        break
      case 'ne':
        newRect.y = startRect.y + dy
        newRect.width = startRect.width + dx
        newRect.height = startRect.height - dy
        break
      case 'sw':
        newRect.x = startRect.x + dx
        newRect.width = startRect.width - dx
        newRect.height = startRect.height + dy
        break
      case 'se':
        newRect.width = startRect.width + dx
        newRect.height = startRect.height + dy
        break
      case 'n':
        newRect.y = startRect.y + dy
        newRect.height = startRect.height - dy
        break
      case 's':
        newRect.height = startRect.height + dy
        break
      case 'w':
        newRect.x = startRect.x + dx
        newRect.width = startRect.width - dx
        break
      case 'e':
        newRect.width = startRect.width + dx
        break
    }

    // 移除最小尺寸限制，允许用户自由调整大小
    selectionRect.value = newRect
    drawSelection()
  }
}

const onMouseUp = (e: MouseEvent) => {
  if (!isSelectionMode.value) return

  if (isDragging.value) {
    isDragging.value = false
    dragEnd.value = getCanvasCoords(e)

    const x = Math.min(dragStart.value.x, dragEnd.value.x)
    const y = Math.min(dragStart.value.y, dragEnd.value.y)
    const width = Math.abs(dragEnd.value.x - dragStart.value.x)
    const height = Math.abs(dragEnd.value.y - dragStart.value.y)

    if (width < 50 || height < 50) {
      showMessage('选区太小，请重新框选（最小50x50像素）', 'error')
      selectionRect.value = null
      drawSelection()
      return
    }

    selectionRect.value = { x, y, width, height }
    drawSelection()
  } else if (isResizing.value) {
    isResizing.value = false
    resizeHandle.value = ''
    resizeStartRect.value = null
    drawSelection()
  }
}

const onMouseLeave = () => {
  if (isDragging.value) {
    isDragging.value = false
    drawSelection()
  }
  if (isResizing.value) {
    isResizing.value = false
    resizeHandle.value = ''
    resizeStartRect.value = null
    drawSelection()
  }
}

const drawSelection = () => {
  if (!canvasRef.value) return

  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'
  ctx.fillRect(0, 0, canvasRef.value.width, canvasRef.value.height)

  // 1. 清除已保存的标注框区域的遮罩（不包括正在编辑的）
  currentAnnotations.value.forEach((ann, index) => {
    if (isEditingAnnotation.value && editingAnnotationIndex.value === index) {
      // 跳过正在编辑的标注框
      return
    }
    const box = ann.box
    ctx.clearRect(box.x, box.y, box.width, box.height)
  })

  // 2. 绘制当前正在编辑的选区
  let rect: { x: number; y: number; width: number; height: number }

  if (isDragging.value) {
    const x = Math.min(dragStart.value.x, dragEnd.value.x)
    const y = Math.min(dragStart.value.y, dragEnd.value.y)
    const width = Math.abs(dragEnd.value.x - dragStart.value.x)
    const height = Math.abs(dragEnd.value.y - dragStart.value.y)
    rect = { x, y, width, height }
  } else if (selectionRect.value) {
    rect = selectionRect.value
  } else {
    // 如果没有当前选区，只绘制已保存的标注框
    currentAnnotations.value.forEach((ann) => {
      const box = ann.box
      const annotationColor = ann.color

      ctx.strokeStyle = annotationColor
      ctx.lineWidth = 2
      ctx.strokeRect(box.x, box.y, box.width, box.height)

      ctx.fillStyle = annotationColor
      ctx.font = 'bold 14px monospace'
      ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
      ctx.shadowBlur = 4
      const label = ann.className
      const labelWidth = ctx.measureText(label).width
      ctx.fillRect(box.x, box.y - 20, labelWidth + 8, 20)
      ctx.fillStyle = '#ffffff'
      ctx.fillText(label, box.x + 4, box.y - 5)
      ctx.shadowBlur = 0
    })
    return
  }

  ctx.clearRect(rect.x, rect.y, rect.width, rect.height)

  // 重新绘制已保存的标注框（在当前选区的clearRect之后，不包括正在编辑的）
  currentAnnotations.value.forEach((ann, index) => {
    if (isEditingAnnotation.value && editingAnnotationIndex.value === index) {
      // 跳过正在编辑的标注框
      return
    }
    const box = ann.box
    const annotationColor = ann.color

    ctx.strokeStyle = annotationColor
    ctx.lineWidth = 2
    ctx.strokeRect(box.x, box.y, box.width, box.height)

    ctx.fillStyle = annotationColor
    ctx.font = 'bold 14px monospace'
    ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
    ctx.shadowBlur = 4
    const label = ann.className
    const labelWidth = ctx.measureText(label).width
    ctx.fillRect(box.x, box.y - 20, labelWidth + 8, 20)
    ctx.fillStyle = '#ffffff'
    ctx.fillText(label, box.x + 4, box.y - 5)
    ctx.shadowBlur = 0
  })

  // 使用选中类名的颜色，如果没有选中则使用默认颜色
  let boxColor = '#00ff00' // 默认绿色
  if (selectedClassId.value) {
    const selectedClass = displayedClasses.value.find((c) => c.id === selectedClassId.value)
    if (selectedClass) {
      boxColor = selectedClass.color
    }
  }

  ctx.strokeStyle = isDragging.value ? '#fbbf24' : boxColor
  ctx.lineWidth = 2
  ctx.strokeRect(rect.x, rect.y, rect.width, rect.height)

  const cornerSize = 12
  ctx.strokeStyle = isDragging.value ? '#fbbf24' : boxColor
  ctx.lineWidth = 3

  ctx.beginPath()
  ctx.moveTo(rect.x, rect.y + cornerSize)
  ctx.lineTo(rect.x, rect.y)
  ctx.lineTo(rect.x + cornerSize, rect.y)
  ctx.stroke()

  ctx.beginPath()
  ctx.moveTo(rect.x + rect.width - cornerSize, rect.y)
  ctx.lineTo(rect.x + rect.width, rect.y)
  ctx.lineTo(rect.x + rect.width, rect.y + cornerSize)
  ctx.stroke()

  ctx.beginPath()
  ctx.moveTo(rect.x, rect.y + rect.height - cornerSize)
  ctx.lineTo(rect.x, rect.y + rect.height)
  ctx.lineTo(rect.x + cornerSize, rect.y + rect.height)
  ctx.stroke()

  ctx.beginPath()
  ctx.moveTo(rect.x + rect.width - cornerSize, rect.y + rect.height)
  ctx.lineTo(rect.x + rect.width, rect.y + rect.height)
  ctx.lineTo(rect.x + rect.width, rect.y + rect.height - cornerSize)
  ctx.stroke()

  ctx.fillStyle = isDragging.value ? '#fbbf24' : boxColor
  ctx.font = 'bold 16px monospace'
  ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
  ctx.shadowBlur = 4
  const sizeText = `${Math.round(rect.width)}x${Math.round(rect.height)}`
  ctx.fillText(sizeText, rect.x + 8, rect.y + 24)
  ctx.shadowBlur = 0

  if (selectionRect.value && !isDragging.value && !isResizing.value) {
    const handleSize = 10
    const handles = [
      { x: rect.x, y: rect.y },
      { x: rect.x + rect.width, y: rect.y },
      { x: rect.x, y: rect.y + rect.height },
      { x: rect.x + rect.width, y: rect.y + rect.height },
      { x: rect.x + rect.width / 2, y: rect.y },
      { x: rect.x + rect.width / 2, y: rect.y + rect.height },
      { x: rect.x, y: rect.y + rect.height / 2 },
      { x: rect.x + rect.width, y: rect.y + rect.height / 2 },
    ]

    handles.forEach((handle) => {
      // 绘制圆形拖动点
      ctx.beginPath()
      ctx.arc(handle.x, handle.y, handleSize / 2, 0, Math.PI * 2)
      ctx.fillStyle = boxColor
      ctx.fill()
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.stroke()
    })
  }
}

// 添加标注到内存
const addAnnotation = () => {
  if (!selectionRect.value || !selectedClassId.value) {
    showMessage('请先框选区域并选择类名', 'error')
    return
  }

  const selectedClass = displayedClasses.value.find((c) => c.id === selectedClassId.value)
  if (!selectedClass) return

  // 添加标注到数组
  currentAnnotations.value.push({
    box: { ...selectionRect.value },
    classId: selectedClassId.value,
    className: selectedClass.name,
    color: selectedClass.color,
  })

  showMessage(
    `已添加标注: ${selectedClass.name}，共${currentAnnotations.value.length}个`,
    'success',
  )

  // 清除当前选区，准备下一个标注
  selectionRect.value = null
  drawSelection()
}

// 保存所有标注
const saveAllAnnotations = async () => {
  if (!videoRef.value) return

  if (currentAnnotations.value.length === 0) {
    showMessage('请先添加至少一个标注', 'error')
    return
  }

  const videoWidth = videoRef.value.videoWidth
  const videoHeight = videoRef.value.videoHeight

  // 1. 创建完整视频帧
  const fullFrameCanvas = document.createElement('canvas')
  fullFrameCanvas.width = videoWidth
  fullFrameCanvas.height = videoHeight
  const fullFrameCtx = fullFrameCanvas.getContext('2d')
  if (!fullFrameCtx) return

  fullFrameCtx.drawImage(videoRef.value, 0, 0, videoWidth, videoHeight)

  // 2. 创建640x640的输出canvas
  const finalCanvas = document.createElement('canvas')
  finalCanvas.width = OUTPUT_SIZE
  finalCanvas.height = OUTPUT_SIZE
  const finalCtx = finalCanvas.getContext('2d')
  if (!finalCtx) return

  finalCtx.fillStyle = LETTERBOX_COLOR
  finalCtx.fillRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE)

  // 3. 计算缩放
  const scale = Math.min(OUTPUT_SIZE / videoWidth, OUTPUT_SIZE / videoHeight)
  const scaledWidth = videoWidth * scale
  const scaledHeight = videoHeight * scale
  const offsetX = (OUTPUT_SIZE - scaledWidth) / 2
  const offsetY = (OUTPUT_SIZE - scaledHeight) / 2

  finalCtx.drawImage(fullFrameCanvas, offsetX, offsetY, scaledWidth, scaledHeight)

  // 4. 计算所有标注的YOLO坐标
  const annotations = currentAnnotations.value.map((ann) => {
    const box = ann.box
    const scaledBoxX = offsetX + box.x * scale
    const scaledBoxY = offsetY + box.y * scale
    const scaledBoxWidth = box.width * scale
    const scaledBoxHeight = box.height * scale

    return {
      class_id: ann.classId,
      class_name: ann.className,
      original_box: {
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height,
      },
      output_box: {
        x: scaledBoxX,
        y: scaledBoxY,
        width: scaledBoxWidth,
        height: scaledBoxHeight,
      },
      yolo_format: {
        x_center: (scaledBoxX + scaledBoxWidth / 2) / OUTPUT_SIZE,
        y_center: (scaledBoxY + scaledBoxHeight / 2) / OUTPUT_SIZE,
        width: scaledBoxWidth / OUTPUT_SIZE,
        height: scaledBoxHeight / OUTPUT_SIZE,
      },
    }
  })

  finalCanvas.toBlob(async (blob) => {
    if (!blob) return

    const formData = new FormData()
    formData.append('image', blob, `frame_${Date.now()}.png`)

    if (currentVideoFilename.value) {
      formData.append('video_filename', currentVideoFilename.value)
    }

    // 添加所有标注数据
    formData.append(
      'annotations',
      JSON.stringify({
        video_size: { width: videoWidth, height: videoHeight },
        scaled_frame: {
          x: offsetX,
          y: offsetY,
          width: scaledWidth,
          height: scaledHeight,
          scale: scale,
        },
        annotations: annotations,
      }),
    )

    try {
      showMessage('正在保存截图和标注...', 'info')
      const response = await fetch(`${API_BASE_URL}/api/save-frame-multi`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) throw new Error('保存失败')

      const data = await response.json()
      showMessage(`保存成功: ${annotations.length}个标注`, 'success')

      // 清空标注列表
      currentAnnotations.value = []

      // 退出框选模式
      isSelectionMode.value = false

      loadFrames()
    } catch (error) {
      console.error('保存失败:', error)
      showMessage('保存失败', 'error')
    }
  }, 'image/png')
}

// ==================== ClassGroupManager 事件处理 ====================

const onSelectClass = (classId: number) => {
  selectedClassId.value = classId
}

const onClassChange = () => {
  // 当切换类名时，如果当前有选区，重新绘制以更新颜色
  if (selectionRect.value) {
    drawSelection()
  }
}

const finishEditAnnotation = () => {
  if (
    isEditingAnnotation.value &&
    editingAnnotationIndex.value !== null &&
    selectionRect.value &&
    selectedClassId.value
  ) {
    const selectedClass = displayedClasses.value.find((c) => c.id === selectedClassId.value)
    if (selectedClass) {
      // 更新标注
      currentAnnotations.value[editingAnnotationIndex.value] = {
        box: { ...selectionRect.value },
        classId: selectedClassId.value,
        className: selectedClass.name,
        color: selectedClass.color,
      }
      showMessage('标注编辑完成', 'success')
    }
  }

  isEditingAnnotation.value = false
  editingAnnotationIndex.value = null
  selectionRect.value = null
  drawSelection()
}

const deleteEditingAnnotation = () => {
  if (isEditingAnnotation.value && editingAnnotationIndex.value !== null) {
    currentAnnotations.value.splice(editingAnnotationIndex.value, 1)
    showMessage('标注已删除', 'success')

    isEditingAnnotation.value = false
    editingAnnotationIndex.value = null
    selectionRect.value = null
    drawSelection()
  }
}

const onGroupChanged = (groupId: number | null, classes: Class[]) => {
  // 更新当前组的类名列表
  groupClasses.value = classes
  console.log('当前选中的类名组ID:', groupId, '类名数量:', classes.length)
}

const onClassAdded = async () => {
  // 当添加新类名时，重新加载所有类名列表
  await loadClasses()
}

// ==================== 类名管理函数 ====================

const loadClasses = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/classes`)
    if (!response.ok) throw new Error('获取类名列表失败')
    const data = await response.json()

    allClasses.value = data.all_classes
    globalClasses.value = data.global_classes
  } catch (error) {
    console.error('加载类名列表失败:', error)
    showMessage('加载类名列表失败', 'error')
  }
}

const onVideoLoaded = () => {
  console.log('视频加载完成')
  showMessage('视频加载完成', 'success')
}

// 图片预览功能
const showPreview = ref(false)
const previewImageUrl = ref('')
const previewImageData = ref<any>(null)

const previewFrame = async (frame: Frame) => {
  try {
    console.log('开始预览图片:', frame.filename)

    // 先显示模态框
    showPreview.value = true

    // 获取图片的标注数据
    const response = await fetch(`${API_BASE_URL}/api/frames/${frame.filename}/annotations`)
    if (response.ok) {
      const data = await response.json()
      previewImageData.value = data
      console.log('获取到标注数据:', data)
    } else {
      previewImageData.value = null
      console.log('没有标注数据')
    }

    // 等待下一帧确保 DOM 已更新
    await new Promise((resolve) => setTimeout(resolve, 0))

    // 加载图片并绘制
    const img = new Image()
    img.crossOrigin = 'anonymous'

    img.onload = () => {
      console.log('图片加载成功, 尺寸:', img.width, 'x', img.height)

      if (!previewCanvasRef.value) {
        console.error('Canvas ref 不存在')
        return
      }

      const canvas = previewCanvasRef.value
      canvas.width = img.width
      canvas.height = img.height

      const ctx = canvas.getContext('2d')
      if (!ctx) {
        console.error('无法获取 canvas context')
        return
      }

      // 绘制图片
      ctx.drawImage(img, 0, 0)
      console.log('图片已绘制到 canvas')

      // 如果有标注数据，绘制标注框
      if (
        previewImageData.value?.annotations &&
        Array.isArray(previewImageData.value.annotations)
      ) {
        console.log('开始绘制标注框, 数量:', previewImageData.value.annotations.length)

        previewImageData.value.annotations.forEach((ann: any, index: number) => {
          const box = ann.output_box
          console.log(`标注 ${index}:`, box)

          // 使用类名颜色或默认颜色
          // 从所有可能的类名列表中查找
          let color = '#00ff00'
          const allClassLists = [groupClasses.value, globalClasses.value, allClasses.value]
          for (const classList of allClassLists) {
            if (classList && classList.length > 0) {
              const classInfo = classList.find((c) => c.id === ann.class_id)
              if (classInfo) {
                color = classInfo.color
                break
              }
            }
          }

          // 绘制矩形框
          ctx.strokeStyle = color
          ctx.lineWidth = 3
          ctx.strokeRect(box.x, box.y, box.width, box.height)

          // 绘制类名标签
          ctx.fillStyle = color
          ctx.font = 'bold 16px monospace'
          ctx.shadowColor = 'rgba(0, 0, 0, 0.8)'
          ctx.shadowBlur = 4
          const label = ann.class_name
          const labelWidth = ctx.measureText(label).width
          ctx.fillRect(box.x, box.y - 24, labelWidth + 12, 24)
          ctx.fillStyle = '#ffffff'
          ctx.fillText(label, box.x + 6, box.y - 6)
          ctx.shadowBlur = 0
        })

        console.log('标注框绘制完成')
      }
    }

    img.onerror = (e) => {
      console.error('图片加载失败:', e)
      showMessage('图片加载失败', 'error')
      showPreview.value = false
    }

    img.src = `${API_BASE_URL}${frame.path}`
    console.log('开始加载图片:', img.src)
  } catch (error) {
    console.error('预览图片失败:', error)
    showMessage('加载图片失败', 'error')
    showPreview.value = false
  }
}

const closePreview = () => {
  showPreview.value = false
  previewImageUrl.value = ''
  previewImageData.value = null
}
</script>

<style scoped lang="scss">
@use '@/styles/glassmorphism.scss';

.video-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.overlay-canvas {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  cursor: crosshair;
}
</style>
