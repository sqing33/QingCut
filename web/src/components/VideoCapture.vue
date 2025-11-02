<template>
  <div class="video-capture-container">
    <!-- 视频容器 -->
    <div class="video-wrapper" ref="videoWrapper">
      <video 
        ref="videoRef" 
        @loadedmetadata="onVideoLoaded"
        crossorigin="anonymous"
        class="video-element"
      >
        <source v-if="videoUrl" :src="videoUrl" type="video/mp4">
      </video>
      
      <!-- Canvas 叠加层用于显示框选区域 -->
      <canvas 
        ref="canvasRef" 
        class="overlay-canvas"
        @mousemove="onMouseMove"
        @click="captureFrame"
        v-show="isSelectionMode"
      ></canvas>
    </div>

    <!-- 控制按钮 -->
    <div class="controls">
      <label class="upload-btn">
        <input type="file" @change="uploadVideo" accept="video/*" class="hidden">
        <span class="btn-icon">📁</span>
        上传视频
      </label>
      <button @click="togglePlay" class="play-btn" :disabled="!videoUrl">
        <span class="btn-icon">{{ isPlaying ? '⏸️' : '▶️' }}</span>
        {{ isPlaying ? '暂停' : '播放' }}
      </button>
      <button @click="toggleSelectionMode" class="select-btn" :disabled="!videoUrl">
        <span class="btn-icon">{{ isSelectionMode ? '❌' : '✂️' }}</span>
        {{ isSelectionMode ? '取消框选' : '开启框选' }}
      </button>
    </div>

    <!-- 状态提示 -->
    <div v-if="message" class="alert mt-4" :class="messageType">
      <span>{{ message }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { API_BASE_URL } from '@/config'

const videoRef = ref<HTMLVideoElement>()
const canvasRef = ref<HTMLCanvasElement>()
const videoWrapper = ref<HTMLDivElement>()

const isPlaying = ref(false)
const isSelectionMode = ref(false)
const videoUrl = ref('')
const mousePos = ref({ x: 0, y: 0 })
const message = ref('')
const messageType = ref('alert-info')

const SELECTION_SIZE = 640

// 显示消息
const showMessage = (msg: string, type: 'info' | 'success' | 'error' = 'info') => {
  message.value = msg
  messageType.value = `alert-${type}`
  setTimeout(() => {
    message.value = ''
  }, 3000)
}

// 视频播放/暂停
const togglePlay = () => {
  if (!videoRef.value) return
  
  if (isPlaying.value) {
    videoRef.value.pause()
  } else {
    videoRef.value.play()
  }
  isPlaying.value = !isPlaying.value
}

// 开启/关闭框选模式
const toggleSelectionMode = () => {
  isSelectionMode.value = !isSelectionMode.value
  if (isSelectionMode.value) {
    videoRef.value?.pause()
    isPlaying.value = false
    setupCanvas()
    showMessage('框选模式已开启，移动鼠标并点击截取图片', 'info')
  } else {
    showMessage('框选模式已关闭', 'info')
  }
}

// 设置 Canvas 尺寸与视频一致
const setupCanvas = () => {
  if (!canvasRef.value || !videoRef.value) return
  
  canvasRef.value.width = videoRef.value.videoWidth
  canvasRef.value.height = videoRef.value.videoHeight
}

// 鼠标移动时绘制框选区域
const onMouseMove = (e: MouseEvent) => {
  if (!canvasRef.value || !isSelectionMode.value) return
  
  const rect = canvasRef.value.getBoundingClientRect()
  const scaleX = canvasRef.value.width / rect.width
  const scaleY = canvasRef.value.height / rect.height
  
  mousePos.value = {
    x: (e.clientX - rect.left) * scaleX,
    y: (e.clientY - rect.top) * scaleY
  }
  
  drawSelection()
}

// 绘制框选区域
const drawSelection = () => {
  if (!canvasRef.value) return
  
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return
  
  // 清除画布
  ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  
  // 计算框选区域中心位置
  let x = mousePos.value.x - SELECTION_SIZE / 2
  let y = mousePos.value.y - SELECTION_SIZE / 2
  
  // 边界检查
  x = Math.max(0, Math.min(x, canvasRef.value.width - SELECTION_SIZE))
  y = Math.max(0, Math.min(y, canvasRef.value.height - SELECTION_SIZE))
  
  // 绘制半透明背景
  ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'
  ctx.fillRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  
  // 清除框选区域（显示视频）
  ctx.clearRect(x, y, SELECTION_SIZE, SELECTION_SIZE)
  
  // 绘制框选边框
  ctx.strokeStyle = '#00ff00'
  ctx.lineWidth = 3
  ctx.strokeRect(x, y, SELECTION_SIZE, SELECTION_SIZE)
  
  // 绘制中心十字线
  ctx.strokeStyle = '#00ff00'
  ctx.lineWidth = 1
  const centerX = x + SELECTION_SIZE / 2
  const centerY = y + SELECTION_SIZE / 2
  ctx.beginPath()
  ctx.moveTo(centerX - 10, centerY)
  ctx.lineTo(centerX + 10, centerY)
  ctx.moveTo(centerX, centerY - 10)
  ctx.lineTo(centerX, centerY + 10)
  ctx.stroke()
  
  // 显示尺寸信息
  ctx.fillStyle = '#00ff00'
  ctx.font = '14px monospace'
  ctx.fillText(`${SELECTION_SIZE}x${SELECTION_SIZE}`, x + 5, y + 20)
}

// 截取当前帧
const captureFrame = async () => {
  if (!videoRef.value || !isSelectionMode.value) return
  
  // 创建临时 Canvas 用于截图
  const tempCanvas = document.createElement('canvas')
  tempCanvas.width = SELECTION_SIZE
  tempCanvas.height = SELECTION_SIZE
  const ctx = tempCanvas.getContext('2d')
  if (!ctx) return
  
  // 计算截取位置（考虑边界）
  let sx = mousePos.value.x - SELECTION_SIZE / 2
  let sy = mousePos.value.y - SELECTION_SIZE / 2
  
  sx = Math.max(0, Math.min(sx, videoRef.value.videoWidth - SELECTION_SIZE))
  sy = Math.max(0, Math.min(sy, videoRef.value.videoHeight - SELECTION_SIZE))
  
  // 绘制视频帧到临时 Canvas
  ctx.drawImage(
    videoRef.value,
    sx, sy, SELECTION_SIZE, SELECTION_SIZE,
    0, 0, SELECTION_SIZE, SELECTION_SIZE
  )
  
  // 转为 Blob 并上传
  tempCanvas.toBlob(async (blob) => {
    if (!blob) return
    
    const formData = new FormData()
    formData.append('image', blob, `frame_${Date.now()}.png`)
    
    try {
      showMessage('正在保存截图...', 'info')
      const response = await fetch(`${API_BASE_URL}/api/save-frame`, {
        method: 'POST',
        body: formData
      })
      
      if (!response.ok) {
        throw new Error('保存失败')
      }
      
      const data = await response.json()
      showMessage(`截图保存成功: ${data.filename}`, 'success')
      console.log('截图保存成功:', data)
    } catch (error) {
      console.error('截图保存失败:', error)
      showMessage('截图保存失败', 'error')
    }
  }, 'image/png')
}

// 上传视频
const uploadVideo = async (e: Event) => {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  
  const file = input.files[0]
  if (!file) return
  
  const formData = new FormData()
  formData.append('video', file)
  
  try {
    showMessage('正在上传视频...', 'info')
    const response = await fetch(`${API_BASE_URL}/api/upload-video`, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error('上传失败')
    }
    
    const data = await response.json()
    videoUrl.value = `${API_BASE_URL}${data.url}`
    showMessage('视频上传成功', 'success')
    
    // 等待视频加载后自动播放
    setTimeout(() => {
      videoRef.value?.play()
      isPlaying.value = true
    }, 100)
  } catch (error) {
    console.error('视频上传失败:', error)
    showMessage('视频上传失败', 'error')
  }
}

const onVideoLoaded = () => {
  console.log('视频加载完成')
  showMessage('视频加载完成', 'success')
}
</script>

<style scoped>
.video-capture-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 30px;
  background: linear-gradient(135deg, #fef3c7 0%, #d1fae5 100%);
  min-height: 100vh;
  border-radius: 20px;
}

.video-wrapper {
  position: relative;
  display: inline-block;
  background: linear-gradient(135deg, #1e293b, #0f172a);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}

.video-element {
  display: block;
  max-width: 100%;
  height: auto;
  border-radius: 12px;
}

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

.controls {
  margin-top: 30px;
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
  justify-content: center;
}

.hidden {
  display: none;
}

.upload-btn,
.play-btn,
.select-btn {
  padding: 12px 28px;
  border-radius: 50px;
  border: none;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.btn-icon {
  font-size: 20px;
}

.upload-btn {
  background: linear-gradient(135deg, #ff8c42, #ffa500);
  color: white;
}

.upload-btn:hover {
  background: linear-gradient(135deg, #ff7029, #ff8c00);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 140, 66, 0.4);
}

.play-btn {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: white;
}

.play-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #34d367, #16a34a);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(74, 222, 128, 0.4);
}

.select-btn {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: white;
}

.select-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(251, 191, 36, 0.4);
}

.play-btn:disabled,
.select-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.alert {
  margin-top: 20px;
  padding: 16px 24px;
  border-radius: 12px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.alert-info {
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  color: #1e40af;
  border-left: 4px solid #3b82f6;
}

.alert-success {
  background: linear-gradient(135deg, #d1fae5, #a7f3d0);
  color: #065f46;
  border-left: 4px solid #10b981;
}

.alert-error {
  background: linear-gradient(135deg, #fee2e2, #fecaca);
  color: #991b1b;
  border-left: 4px solid #ef4444;
}

@media (max-width: 768px) {
  .video-capture-container {
    padding: 20px;
  }

  .controls {
    gap: 10px;
  }

  .upload-btn,
  .play-btn,
  .select-btn {
    padding: 10px 20px;
    font-size: 14px;
  }

  .btn-icon {
    font-size: 16px;
  }
}
</style>
