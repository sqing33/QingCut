<template>
  <div v-if="show" class="modal modal-open" @click.self="closeModal">
    <div class="modal-box max-w-7xl w-full h-[90vh] flex flex-col p-0">
      <!-- 头部 -->
      <div class="flex items-center justify-between p-3 border-b border-base-300 flex-shrink-0">
        <div class="flex items-center gap-2 flex-1 justify-center">
          <h2 class="text-lg font-bold">🖼️ 图片预览</h2>
          <span class="text-sm text-base-content/60">{{ imageInfo.filename }}</span>
        </div>
        <button @click="closeModal" class="btn btn-sm btn-circle btn-ghost">✕</button>
      </div>

      <!-- 主体内容 -->
      <div class="flex-1 flex overflow-hidden">
        <!-- 左侧图片显示区域 -->
        <div class="flex-1 relative flex flex-col" ref="imageContainer">
          <div
            class="flex-1 relative flex items-center justify-center p-4 bg-base-200"
            ref="imageWrapper"
          >
            <img
              v-if="imageUrl"
              ref="imageRef"
              :src="imageUrl"
              @load="onImageLoaded"
              class="max-w-full max-h-full object-contain"
              style="display: block"
            />

            <!-- Canvas 叠加层用于绘制标注框 -->
            <canvas
              ref="canvasRef"
              class="absolute top-0 left-0"
              :class="{ 'cursor-crosshair': isEditMode }"
              @mousedown="onMouseDown"
              @mousemove="onMouseMove"
              @mouseup="onMouseUp"
              @mouseleave="onMouseLeave"
              v-show="imageLoaded"
            ></canvas>

            <!-- 编辑工具栏（编辑模式下显示） -->
            <div
              v-if="isEditMode && currentSelection"
              class="absolute top-4 right-4 bg-base-100 shadow-2xl rounded-lg p-3 border border-base-300 z-10"
            >
              <div class="flex flex-col gap-2">
                <!-- 类名选择 -->
                <div class="flex items-center gap-2">
                  <label class="text-xs font-semibold whitespace-nowrap">类名:</label>
                  <select
                    v-model="selectedClassId"
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
                    v-if="!editingAnnotationIndex && editingAnnotationIndex !== 0"
                    @click="addAnnotation"
                    class="btn btn-xs btn-success flex-1"
                    :disabled="!selectedClassId"
                  >
                    ➕ 添加
                  </button>
                  <button
                    v-if="editingAnnotationIndex !== null"
                    @click="finishEditAnnotation"
                    class="btn btn-xs btn-primary flex-1"
                  >
                    ✓ 完成
                  </button>
                  <button
                    v-if="editingAnnotationIndex !== null"
                    @click="deleteAnnotation"
                    class="btn btn-xs btn-error"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部键盘提示 - 只占图片区域宽度 -->
          <div
            class="flex items-center justify-between gap-2 px-4 py-3 border-t border-base-300 text-xs flex-shrink-0 bg-base-100"
          >
            <div class="flex gap-2">
              <div class="flex items-center gap-1">
                <kbd class="kbd kbd-xs">R</kbd>
                <span class="text-base-content/60">编辑模式</span>
              </div>
              <div v-if="isEditMode" class="flex items-center gap-1">
                <kbd class="kbd kbd-xs">Enter</kbd>
                <span class="text-base-content/60">添加/完成</span>
              </div>
              <div v-if="isEditMode" class="flex items-center gap-1">
                <kbd class="kbd kbd-xs">Del</kbd>
                <span class="text-base-content/60">删除</span>
              </div>
              <div v-if="isEditMode" class="flex items-center gap-1">
                <kbd class="kbd kbd-xs">Esc</kbd>
                <span class="text-base-content/60">取消</span>
              </div>
            </div>
            <button
              v-if="editable"
              @click="toggleEditMode"
              class="btn btn-sm"
              :class="isEditMode ? 'btn-warning' : 'btn-ghost'"
            >
              {{ isEditMode ? '✓ 完成编辑' : '✏️ 编辑标注' }}
            </button>
          </div>
        </div>

        <!-- 右侧面板：标注列表 + 类名管理 -->
        <div class="w-80 border-l border-base-300 flex flex-col bg-base-100">
          <!-- 标注列表区域 (上半部分) -->
          <div class="flex-1 border-b border-base-300 flex flex-col min-h-0">
            <div class="p-4 border-b border-base-300 flex-shrink-0">
              <div class="flex items-center justify-between">
                <h3 class="font-bold">
                  📋 标注列表
                  <span class="badge badge-primary ml-2">{{ localAnnotations.length }}</span>
                </h3>
                <button
                  v-if="editable && hasChanges"
                  @click="saveAnnotations"
                  class="btn btn-xs btn-success"
                >
                  💾 保存
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto p-4 min-h-0">
              <div
                v-if="localAnnotations.length === 0"
                class="text-center py-8 text-base-content/60"
              >
                <div class="text-4xl mb-2">📝</div>
                <p class="text-sm">暂无标注</p>
                <p class="text-xs mt-1">点击"编辑标注"开始添加</p>
              </div>

              <div v-else class="space-y-2">
                <div
                  v-for="(annotation, index) in localAnnotations"
                  :key="index"
                  class="card bg-base-200 p-2 cursor-pointer hover:shadow-lg transition-all"
                  :class="{ 'ring-2 ring-primary': editingAnnotationIndex === index }"
                  @click="selectAnnotation(index)"
                >
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-2 flex-1 min-w-0">
                      <div
                        class="w-4 h-4 rounded flex-shrink-0"
                        :style="{ backgroundColor: getClassColor(annotation.class_id) }"
                      ></div>
                      <span class="font-semibold text-sm truncate">{{ annotation.class_name }}</span>
                    </div>
                    <div class="flex items-center gap-1 flex-shrink-0">
                      <span class="text-xs text-base-content/60 whitespace-nowrap">
                        {{ Math.round(annotation.box.width) }}×{{ Math.round(annotation.box.height) }}
                      </span>
                      <button
                        v-if="isEditMode"
                        @click.stop="() => deleteAnnotation(index)"
                        class="btn btn-xs btn-ghost btn-circle"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 类名管理区域 (下半部分) -->
          <div class="flex-1 glass-panel-light flex flex-col min-h-0">
            <div class="p-4 flex-shrink-0">
              <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-bold">🏷️ 类名管理</h2>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto px-4 pb-4 min-h-0">
              <ClassGroupManager
                :selected-class-id="selectedClassId"
                @select-class="onSelectClass"
                @group-changed="onGroupChanged"
                @show-message="showMessageFromChild"
                @class-added="onClassAdded"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 消息提示 -->
    <div v-if="message" class="toast toast-top toast-center">
      <div :class="['alert', messageType]">
        <span>{{ message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import ClassGroupManager from './ClassGroupManager.vue'

interface Annotation {
  class_id: number
  class_name: string
  box: {
    x: number
    y: number
    width: number
    height: number
  }
}

interface Class {
  id: number
  name: string
  color: string
}

interface ImageInfo {
  filename: string
  path: string
}

const props = defineProps<{
  show: boolean
  imageUrl: string
  imageInfo: ImageInfo
  annotations: Annotation[]
  availableClasses: Class[]
  editable?: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', annotations: Annotation[]): void
  (e: 'refreshClasses'): void
}>()

const imageRef = ref<HTMLImageElement>()
const canvasRef = ref<HTMLCanvasElement>()
const imageWrapper = ref<HTMLDivElement>()

const isEditMode = ref(false)
const imageLoaded = ref(false)
const localAnnotations = ref<Annotation[]>([])
const selectedClassId = ref<number | null>(null)
const message = ref('')
const messageType = ref('alert-info')

// 类名管理状态
const groupClasses = ref<Class[]>([])

// 绘制相关状态
const isDragging = ref(false)
const isResizing = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const dragEnd = ref({ x: 0, y: 0 })
const currentSelection = ref<{ x: number; y: number; width: number; height: number } | null>(null)
const editingAnnotationIndex = ref<number | null>(null)
const resizeHandle = ref<string>('')
const resizeStartRect = ref<{ x: number; y: number; width: number; height: number } | null>(null)

const hasChanges = computed(() => {
  return JSON.stringify(localAnnotations.value) !== JSON.stringify(props.annotations)
})

const displayedClasses = computed(() => {
  // 优先使用从ClassGroupManager传递过来的类名列表
  if (groupClasses.value.length > 0) {
    return groupClasses.value
  }
  // 如果没有选中组，使用全局类名作为后备
  return props.availableClasses
})

// 监听 annotations 变化
watch(
  () => props.annotations,
  (newAnnotations) => {
    localAnnotations.value = JSON.parse(JSON.stringify(newAnnotations))
    // 当标注数据变化时，如果图片已加载，重新绘制标注
    if (imageLoaded.value) {
      nextTick(() => {
        drawAnnotations()
      })
    }
  },
  { immediate: true, deep: true },
)

// 监听显示状态
watch(
  () => props.show,
  (newShow) => {
    if (newShow) {
      imageLoaded.value = false
      isEditMode.value = false
      currentSelection.value = null
      editingAnnotationIndex.value = null
      selectedClassId.value = null
    }
  },
)

const onImageLoaded = () => {
  imageLoaded.value = true
  nextTick(() => {
    setupCanvas()
    drawAnnotations()
  })
}

const setupCanvas = () => {
  if (!canvasRef.value || !imageRef.value || !imageWrapper.value) return

  const img = imageRef.value
  const wrapper = imageWrapper.value
  const wrapperRect = wrapper.getBoundingClientRect()

  // 计算图片在容器中的实际显示尺寸
  const imgAspect = img.naturalWidth / img.naturalHeight
  const wrapperAspect = wrapperRect.width / wrapperRect.height

  let displayWidth, displayHeight
  if (wrapperAspect > imgAspect) {
    displayHeight = wrapperRect.height - 32 // 减去 padding
    displayWidth = displayHeight * imgAspect
  } else {
    displayWidth = wrapperRect.width - 32
    displayHeight = displayWidth / imgAspect
  }

  // 设置 canvas 尺寸为图片的原始分辨率
  canvasRef.value.width = img.naturalWidth
  canvasRef.value.height = img.naturalHeight
  canvasRef.value.style.width = `${displayWidth}px`
  canvasRef.value.style.height = `${displayHeight}px`

  // 居中定位
  const left = (wrapperRect.width - displayWidth) / 2
  const top = (wrapperRect.height - displayHeight) / 2
  canvasRef.value.style.left = `${left}px`
  canvasRef.value.style.top = `${top}px`
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

const getAnnotationAtPoint = (x: number, y: number): number => {
  const threshold = 5
  for (let i = localAnnotations.value.length - 1; i >= 0; i--) {
    const ann = localAnnotations.value[i]
    if (!ann.box) continue

    const box = ann.box
    const onBorder =
      ((Math.abs(x - box.x) < threshold || Math.abs(x - (box.x + box.width)) < threshold) &&
        y >= box.y - threshold &&
        y <= box.y + box.height + threshold) ||
      ((Math.abs(y - box.y) < threshold || Math.abs(y - (box.y + box.height)) < threshold) &&
        x >= box.x - threshold &&
        x <= box.x + box.width + threshold)

    if (onBorder) return i
  }
  return -1
}

const onMouseDown = (e: MouseEvent) => {
  if (!isEditMode.value) return

  const coords = getCanvasCoords(e)

  // 检查是否点击了当前选区的调整手柄
  if (currentSelection.value) {
    const handle = getResizeHandle(coords.x, coords.y, currentSelection.value)
    if (handle) {
      isResizing.value = true
      resizeHandle.value = handle
      resizeStartRect.value = { ...currentSelection.value }
      dragStart.value = coords
      return
    }
  }

  // 检查是否点击了已有标注
  const annotationIndex = getAnnotationAtPoint(coords.x, coords.y)
  if (annotationIndex !== -1) {
    selectAnnotation(annotationIndex)

    const ann = localAnnotations.value[annotationIndex]
    if (ann?.box) {
      const handle = getResizeHandle(coords.x, coords.y, ann.box)
      if (handle) {
        isResizing.value = true
        resizeHandle.value = handle
        resizeStartRect.value = { ...ann.box }
        dragStart.value = coords
      }
    }
    return
  }

  // 开始新的框选
  isDragging.value = true
  dragStart.value = coords
  dragEnd.value = coords
  currentSelection.value = null
  editingAnnotationIndex.value = null
}

const onMouseMove = (e: MouseEvent) => {
  if (!isEditMode.value) return

  const coords = getCanvasCoords(e)

  if (isDragging.value) {
    dragEnd.value = coords
    drawAnnotations()
  } else if (isResizing.value && resizeStartRect.value && currentSelection.value) {
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

    currentSelection.value = newRect
    drawAnnotations()
  }
}

const onMouseUp = (e: MouseEvent) => {
  if (!isEditMode.value) return

  if (isDragging.value) {
    isDragging.value = false
    dragEnd.value = getCanvasCoords(e)

    const x = Math.min(dragStart.value.x, dragEnd.value.x)
    const y = Math.min(dragStart.value.y, dragEnd.value.y)
    const width = Math.abs(dragEnd.value.x - dragStart.value.x)
    const height = Math.abs(dragEnd.value.y - dragStart.value.y)

    if (width < 20 || height < 20) {
      showMessage('选区太小，请重新框选', 'alert-error')
      currentSelection.value = null
      drawAnnotations()
      return
    }

    currentSelection.value = { x, y, width, height }
    drawAnnotations()
  } else if (isResizing.value) {
    isResizing.value = false
    resizeHandle.value = ''
    resizeStartRect.value = null
  }
}

const onMouseLeave = () => {
  if (isDragging.value) {
    isDragging.value = false
  }
  if (isResizing.value) {
    isResizing.value = false
    resizeHandle.value = ''
    resizeStartRect.value = null
  }
}

const drawAnnotations = () => {
  if (!canvasRef.value) return

  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)

  // 绘制已保存的标注（不包括正在编辑的）
  localAnnotations.value.forEach((ann, index) => {
    if (editingAnnotationIndex.value === index) return

    if (ann.box) {
      const color = getClassColor(ann.class_id)
      const box = ann.box

      ctx.strokeStyle = color
      ctx.lineWidth = 2
      ctx.strokeRect(box.x, box.y, box.width, box.height)

      ctx.fillStyle = color
      ctx.font = 'bold 14px Arial'
      const label = ann.class_name
      const labelWidth = ctx.measureText(label).width
      // 调整标签位置到框内顶部
      const labelY = canvasRef.value && box.y + 20 < canvasRef.value.height ? box.y + 2 : box.y - 20
      ctx.fillRect(box.x, labelY, labelWidth + 8, 20)
      ctx.fillStyle = '#ffffff'
      ctx.fillText(label, box.x + 4, labelY + 15)
    }
  })

  // 绘制当前选区
  let rect: { x: number; y: number; width: number; height: number } | null = null

  if (isDragging.value) {
    const x = Math.min(dragStart.value.x, dragEnd.value.x)
    const y = Math.min(dragStart.value.y, dragEnd.value.y)
    const width = Math.abs(dragEnd.value.x - dragStart.value.x)
    const height = Math.abs(dragEnd.value.y - dragStart.value.y)
    rect = { x, y, width, height }
  } else if (currentSelection.value) {
    rect = currentSelection.value
  }

  if (rect) {
    const boxColor = selectedClassId.value ? getClassColor(selectedClassId.value) : '#00ff00'

    ctx.strokeStyle = isDragging.value ? '#fbbf24' : boxColor
    ctx.lineWidth = 2
    ctx.strokeRect(rect.x, rect.y, rect.width, rect.height)

    // 绘制角标记
    const cornerSize = 12
    ctx.strokeStyle = isDragging.value ? '#fbbf24' : boxColor
    ctx.lineWidth = 3

    // 左上
    ctx.beginPath()
    ctx.moveTo(rect.x, rect.y + cornerSize)
    ctx.lineTo(rect.x, rect.y)
    ctx.lineTo(rect.x + cornerSize, rect.y)
    ctx.stroke()

    // 右上
    ctx.beginPath()
    ctx.moveTo(rect.x + rect.width - cornerSize, rect.y)
    ctx.lineTo(rect.x + rect.width, rect.y)
    ctx.lineTo(rect.x + rect.width, rect.y + cornerSize)
    ctx.stroke()

    // 左下
    ctx.beginPath()
    ctx.moveTo(rect.x, rect.y + rect.height - cornerSize)
    ctx.lineTo(rect.x, rect.y + rect.height)
    ctx.lineTo(rect.x + cornerSize, rect.y + rect.height)
    ctx.stroke()

    // 右下
    ctx.beginPath()
    ctx.moveTo(rect.x + rect.width - cornerSize, rect.y + rect.height)
    ctx.lineTo(rect.x + rect.width, rect.y + rect.height)
    ctx.lineTo(rect.x + rect.width, rect.y + rect.height - cornerSize)
    ctx.stroke()

    // 绘制拖动手柄
    if (currentSelection.value && !isDragging.value && !isResizing.value) {
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
}

const addAnnotation = () => {
  if (!currentSelection.value || !selectedClassId.value) {
    showMessage('请先框选区域并选择类名', 'alert-error')
    return
  }

  const selectedClass = displayedClasses.value.find((c) => c.id === selectedClassId.value)
  if (!selectedClass) return

  const box = currentSelection.value
  const annotation: Annotation = {
    class_id: selectedClassId.value,
    class_name: selectedClass.name,
    box: { ...box },
  }

  localAnnotations.value.push(annotation)
  showMessage(`已添加标注: ${selectedClass.name}`, 'alert-success')

  currentSelection.value = null
  drawAnnotations()
}

const selectAnnotation = (index: number) => {
  if (!isEditMode.value) return

  editingAnnotationIndex.value = index
  const ann = localAnnotations.value[index]
  if (ann && ann.box) {
    currentSelection.value = { ...ann.box }
    selectedClassId.value = ann.class_id
    drawAnnotations()
  }
}

const finishEditAnnotation = () => {
  if (editingAnnotationIndex.value !== null && currentSelection.value && selectedClassId.value) {
    const selectedClass = displayedClasses.value.find((c) => c.id === selectedClassId.value)
    if (selectedClass && localAnnotations.value[editingAnnotationIndex.value]) {
      const box = currentSelection.value
      localAnnotations.value[editingAnnotationIndex.value] = {
        class_id: selectedClassId.value,
        class_name: selectedClass.name,
        box: { ...box },
      }
      showMessage('标注编辑完成', 'alert-success')
    }
  }

  editingAnnotationIndex.value = null
  currentSelection.value = null
  drawAnnotations()
}

const deleteAnnotation = (index?: number) => {
  const targetIndex = index !== undefined ? index : editingAnnotationIndex.value
  if (targetIndex !== null) {
    localAnnotations.value.splice(targetIndex, 1)
    showMessage('标注已删除', 'alert-success')

    editingAnnotationIndex.value = null
    currentSelection.value = null
    drawAnnotations()
  }
}

const toggleEditMode = () => {
  isEditMode.value = !isEditMode.value

  if (!isEditMode.value) {
    // 退出编辑模式时保存更改
    if (hasChanges.value) {
      saveAnnotations()
    }
    currentSelection.value = null
    editingAnnotationIndex.value = null
  }

  drawAnnotations()
}

const saveAnnotations = () => {
  emit('save', localAnnotations.value)
}

const closeModal = () => {
  if (hasChanges.value && isEditMode.value) {
    if (confirm('有未保存的更改，是否保存？')) {
      saveAnnotations()
    }
  }
  emit('close')
}

const getClassColor = (classId: number): string => {
  const cls = displayedClasses.value.find((c) => c.id === classId)
  return cls ? cls.color : '#3b82f6'
}

const showMessage = (msg: string, type: string = 'alert-info') => {
  message.value = msg
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 3000)
}

// ClassGroupManager 事件处理
const onSelectClass = (classId: number) => {
  selectedClassId.value = classId
}

const onGroupChanged = (groupId: number | null, classes: Class[]) => {
  // 更新当前组的类名列表
  groupClasses.value = classes
  console.log('当前选中的类名组ID:', groupId, '类名数量:', classes.length)
}

const showMessageFromChild = (msg: string, type: 'info' | 'success' | 'error') => {
  showMessage(msg, `alert-${type}`)
}

const onClassAdded = () => {
  // 当添加新类名时，通知父组件刷新类名列表
  emit('refreshClasses')
}

// 键盘快捷键 - 使用stopPropagation防止事件冒泡
const handleKeyPress = (e: KeyboardEvent) => {
  if (!props.show) return

  // R键切换编辑模式
  if ((e.key === 'r' || e.key === 'R') && props.editable) {
    e.preventDefault()
    e.stopPropagation()
    toggleEditMode()
    return
  }

  if (!isEditMode.value) return

  if (e.key === 'Enter' && currentSelection.value) {
    e.preventDefault()
    e.stopPropagation()
    if (editingAnnotationIndex.value !== null) {
      finishEditAnnotation()
    } else {
      addAnnotation()
    }
  } else if (
    (e.key === 'Delete' || e.key === 'Backspace') &&
    editingAnnotationIndex.value !== null
  ) {
    e.preventDefault()
    e.stopPropagation()
    deleteAnnotation()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    e.stopPropagation()
    if (currentSelection.value) {
      currentSelection.value = null
      editingAnnotationIndex.value = null
      drawAnnotations()
    } else {
      toggleEditMode()
    }
  }
}

watch(
  () => props.show,
  (show) => {
    if (show) {
      // 使用capture模式优先捕获事件
      window.addEventListener('keydown', handleKeyPress, true)
    } else {
      window.removeEventListener('keydown', handleKeyPress, true)
    }
  },
)
</script>

<style scoped>
.modal-box {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.9) 100%);
  backdrop-filter: blur(20px);
}
</style>
