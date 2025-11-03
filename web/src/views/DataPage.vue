<template>
  <div class="page-container-fixed">
    <!-- 顶部筛选栏 -->
    <div class="glass-panel rounded-2xl shadow-xl p-6 mb-6 flex-shrink-0">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-bold">📊 数据管理</h2>
        <div class="flex gap-2">
          <button @click="loadData" class="btn btn-sm btn-ghost" title="刷新">
            🔄 刷新
          </button>
          <button @click="exportData" class="btn btn-sm btn-primary">
            📥 导出数据
          </button>
        </div>
      </div>

      <!-- 筛选条件 -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- 视频筛选 -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">🎬 视频</span>
          </label>
          <select v-model="filters.videoFilename" class="select select-bordered select-sm">
            <option value="">全部视频</option>
            <option v-for="video in videos" :key="video" :value="video">
              {{ video }}
            </option>
          </select>
        </div>

        <!-- 类名筛选 -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">🏷️ 类名</span>
          </label>
          <select v-model="filters.className" class="select select-bordered select-sm">
            <option value="">全部类名</option>
            <option v-for="cls in classes" :key="cls.id" :value="cls.name">
              {{ cls.name }}
            </option>
          </select>
        </div>

        <!-- 日期范围 -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">📅 日期范围</span>
          </label>
          <select v-model="filters.dateRange" class="select select-bordered select-sm">
            <option value="">全部时间</option>
            <option value="today">今天</option>
            <option value="week">最近一周</option>
            <option value="month">最近一个月</option>
          </select>
        </div>

        <!-- 搜索 -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">🔍 搜索</span>
          </label>
          <input
            v-model="filters.search"
            type="text"
            placeholder="搜索文件名..."
            class="input input-bordered input-sm"
          />
        </div>
      </div>

    </div>

    <!-- 数据表格 -->
    <div class="glass-panel rounded-2xl shadow-xl overflow-hidden flex-1 flex flex-col">
      <!-- 表格容器 -->
      <div class="overflow-x-auto flex-1">
        <table class="table table-zebra table-pin-rows">
          <!-- 表头 -->
          <thead>
            <tr class="bg-base-200">
              <th class="w-12">
                <label>
                  <input
                    type="checkbox"
                    class="checkbox checkbox-sm"
                    @change="toggleSelectAll"
                    :checked="isAllSelected"
                  />
                </label>
              </th>
              <th class="w-24">缩略图</th>
              <th>文件名</th>
              <th>视频来源</th>
              <th>标注数量</th>
              <th>类名</th>
              <th>创建时间</th>
              <th class="w-32">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="text-center py-8">
                <span class="loading loading-spinner loading-lg"></span>
                <p class="mt-2">加载中...</p>
              </td>
            </tr>
            <tr v-else-if="filteredData.length === 0">
              <td colspan="8" class="text-center py-8 text-base-content/60">
                <div class="text-4xl mb-2">📭</div>
                <p>暂无数据</p>
              </td>
            </tr>
            <tr
              v-else
              v-for="item in paginatedData"
              :key="item.filename"
              class="hover"
            >
              <td>
                <label>
                  <input
                    type="checkbox"
                    class="checkbox checkbox-sm"
                    v-model="selectedItems"
                    :value="item.filename"
                  />
                </label>
              </td>
              <td>
                <div class="avatar">
                  <div class="mask mask-squircle w-16 h-16 cursor-pointer" @click="previewImage(item)">
                    <img
                      :src="`${API_BASE_URL}${item.path}`"
                      :alt="item.filename"
                      class="object-cover"
                    />
                  </div>
                </div>
              </td>
              <td>
                <div class="font-medium truncate max-w-xs" :title="item.filename">
                  {{ item.filename }}
                </div>
              </td>
              <td>
                <div class="badge badge-ghost truncate max-w-xs" :title="item.video_filename || '未知'">
                  {{ item.video_filename || '未知' }}
                </div>
              </td>
              <td>
                <div class="badge badge-primary">
                  {{ item.annotation_count || 0 }} 个
                </div>
              </td>
              <td>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="className in item.class_names"
                    :key="className"
                    class="badge badge-sm"
                    :style="{ backgroundColor: getClassColor(className) }"
                  >
                    {{ className }}
                  </span>
                  <span v-if="!item.class_names || item.class_names.length === 0" class="text-base-content/40">
                    无标注
                  </span>
                </div>
              </td>
              <td>
                <div class="text-sm">
                  {{ formatDate(item.created_at) }}
                </div>
              </td>
              <td>
                <div class="flex gap-1">
                  <button
                    @click="previewImage(item)"
                    class="btn btn-xs btn-ghost"
                    title="预览"
                  >
                    👁️
                  </button>
                  <button
                    @click="downloadImage(item)"
                    class="btn btn-xs btn-ghost"
                    title="下载"
                  >
                    📥
                  </button>
                  <button
                    @click="deleteImage(item)"
                    class="btn btn-xs btn-error btn-ghost"
                    title="删除"
                  >
                    🗑️
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="flex items-center justify-between p-4 bg-base-200">
        <div class="text-sm text-base-content/60">
          显示 {{ startIndex + 1 }} - {{ endIndex }} 条，共 {{ filteredData.length }} 条
        </div>
        <div class="join">
          <button
            class="join-item btn btn-sm"
            :disabled="currentPage === 1"
            @click="currentPage--"
          >
            «
          </button>
          <button class="join-item btn btn-sm">
            第 {{ currentPage }} / {{ totalPages }} 页
          </button>
          <button
            class="join-item btn btn-sm"
            :disabled="currentPage === totalPages"
            @click="currentPage++"
          >
            »
          </button>
        </div>
        <select v-model="pageSize" class="select select-bordered select-sm">
          <option :value="10">10 条/页</option>
          <option :value="20">20 条/页</option>
          <option :value="50">50 条/页</option>
          <option :value="100">100 条/页</option>
        </select>
      </div>
    </div>

    <!-- 图片预览模态框 -->
    <ImagePreviewModal
      :show="!!previewItem"
      :image-url="previewImageUrl"
      :image-info="previewImageInfo"
      :annotations="previewAnnotations"
      :available-classes="classes"
      :editable="true"
      @close="closePreview"
      @save="handleSaveAnnotations"
      @refresh-classes="loadClasses"
    />

    <!-- 删除确认对话框 -->
    <div v-if="deleteItem" class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg">⚠️ 确认删除</h3>
        <p class="py-4">确定要删除 "{{ deleteItem.filename }}" 吗？此操作无法撤销。</p>
        <div class="modal-action">
          <button @click="confirmDelete" class="btn btn-error">删除</button>
          <button @click="deleteItem = null" class="btn">取消</button>
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
import { ref, computed, onMounted, watch } from 'vue'
import { API_BASE_URL } from '@/config'
import ImagePreviewModal from '@/components/ImagePreviewModal.vue'

interface Frame {
  filename: string
  path: string
  created_at: number
  video_filename?: string
  annotation_count?: number
  class_names?: string[]
}

interface Class {
  id: number
  name: string
  color: string
}

const loading = ref(false)
const allData = ref<Frame[]>([])
const videos = ref<string[]>([])
const classes = ref<Class[]>([])
const selectedItems = ref<string[]>([])
const previewItem = ref<Frame | null>(null)
const previewImageUrl = ref('')
const previewImageInfo = ref<{ filename: string; path: string }>({ filename: '', path: '' })
const previewAnnotations = ref<any[]>([])
const deleteItem = ref<Frame | null>(null)
const message = ref('')
const messageType = ref('alert-info')

// 筛选条件
const filters = ref({
  videoFilename: '',
  className: '',
  dateRange: '',
  search: ''
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 统计信息
const totalCount = computed(() => allData.value.length)
const annotatedCount = computed(() => 
  allData.value.filter(item => item.annotation_count && item.annotation_count > 0).length
)
const annotationRate = computed(() => 
  totalCount.value > 0 ? Math.round((annotatedCount.value / totalCount.value) * 100) : 0
)

// 筛选数据
const filteredData = computed(() => {
  let data = allData.value

  // 视频筛选
  if (filters.value.videoFilename) {
    data = data.filter(item => item.video_filename === filters.value.videoFilename)
  }

  // 类名筛选
  if (filters.value.className) {
    data = data.filter(item => 
      item.class_names && item.class_names.includes(filters.value.className)
    )
  }

  // 日期筛选
  if (filters.value.dateRange) {
    const now = Date.now() / 1000
    let threshold = 0
    
    switch (filters.value.dateRange) {
      case 'today':
        threshold = now - 24 * 60 * 60
        break
      case 'week':
        threshold = now - 7 * 24 * 60 * 60
        break
      case 'month':
        threshold = now - 30 * 24 * 60 * 60
        break
    }
    
    if (threshold > 0) {
      data = data.filter(item => item.created_at >= threshold)
    }
  }

  // 搜索筛选
  if (filters.value.search) {
    const search = filters.value.search.toLowerCase()
    data = data.filter(item => 
      item.filename.toLowerCase().includes(search) ||
      (item.video_filename && item.video_filename.toLowerCase().includes(search))
    )
  }

  return data
})

// 分页数据
const totalPages = computed(() => Math.ceil(filteredData.value.length / pageSize.value))
const startIndex = computed(() => (currentPage.value - 1) * pageSize.value)
const endIndex = computed(() => Math.min(startIndex.value + pageSize.value, filteredData.value.length))
const paginatedData = computed(() => 
  filteredData.value.slice(startIndex.value, endIndex.value)
)

// 全选
const isAllSelected = computed(() => 
  selectedItems.value.length > 0 && 
  selectedItems.value.length === paginatedData.value.length
)

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedItems.value = []
  } else {
    selectedItems.value = paginatedData.value.map(item => item.filename)
  }
}

// 加载类名列表
const loadClasses = async () => {
  try {
    const classesResponse = await fetch(`${API_BASE_URL}/api/classes`)
    if (classesResponse.ok) {
      const classesData = await classesResponse.json()
      classes.value = classesData.classes || []
    }
  } catch (error) {
    console.error('加载类名列表失败:', error)
  }
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    // 加载截图数据
    const framesResponse = await fetch(`${API_BASE_URL}/api/frames`)
    if (!framesResponse.ok) throw new Error('获取数据失败')
    const framesData = await framesResponse.json()
    
    // 为每个截图加载标注信息
    const framesWithAnnotations = await Promise.all(
      framesData.frames.map(async (frame: Frame) => {
        try {
          const annotationResponse = await fetch(
            `${API_BASE_URL}/api/frames/${frame.filename}/annotations`
          )
          if (annotationResponse.ok) {
            const annotationData = await annotationResponse.json()
            return {
              ...frame,
              annotation_count: annotationData.annotations?.length || 0,
              class_names: annotationData.annotations?.map((ann: any) => ann.class_name) || []
            }
          }
        } catch (error) {
          console.error(`加载 ${frame.filename} 标注失败:`, error)
        }
        return { ...frame, annotation_count: 0, class_names: [] }
      })
    )
    
    allData.value = framesWithAnnotations
    
    // 提取视频列表
    const videoSet = new Set<string>()
    framesWithAnnotations.forEach(frame => {
      if (frame.video_filename) {
        videoSet.add(frame.video_filename)
      }
    })
    videos.value = Array.from(videoSet).sort()
    
    // 加载类名列表
    await loadClasses()
  } catch (error) {
    console.error('加载数据失败:', error)
    showMessage('加载数据失败', 'alert-error')
  } finally {
    loading.value = false
  }
}

// 获取类名颜色
const getClassColor = (className: string) => {
  const cls = classes.value.find(c => c.name === className)
  return cls ? cls.color : '#3b82f6'
}

// 格式化日期
const formatDate = (timestamp: number) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 预览图片
const previewImage = async (item: Frame) => {
  previewItem.value = item
  previewImageUrl.value = `${API_BASE_URL}${item.path}`
  previewImageInfo.value = {
    filename: item.filename,
    path: item.path
  }
  
  // 加载标注数据
  try {
    const response = await fetch(`${API_BASE_URL}/api/frames/${item.filename}/annotations`)
    if (response.ok) {
      const data = await response.json()
      previewAnnotations.value = data.annotations || []
    } else {
      previewAnnotations.value = []
    }
  } catch (error) {
    console.error('加载标注失败:', error)
    previewAnnotations.value = []
  }
}

const closePreview = () => {
  previewItem.value = null
  previewImageUrl.value = ''
  previewAnnotations.value = []
}

const handleSaveAnnotations = async (annotations: any[]) => {
  if (!previewItem.value) return
  
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/frames/${previewItem.value.filename}/annotations`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ annotations })
      }
    )
    
    if (!response.ok) throw new Error('保存标注失败')
    
    showMessage('标注已保存', 'alert-success')
    previewAnnotations.value = annotations
    await loadData()
  } catch (error) {
    console.error('保存标注失败:', error)
    showMessage('保存标注失败', 'alert-error')
  }
}

// 下载图片
const downloadImage = (item: Frame) => {
  const link = document.createElement('a')
  link.href = `${API_BASE_URL}${item.path}`
  link.download = item.filename
  link.click()
  showMessage('开始下载', 'alert-success')
}

// 删除图片
const deleteImage = (item: Frame) => {
  deleteItem.value = item
}

const confirmDelete = async () => {
  if (!deleteItem.value) return
  
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/delete-frame`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          filename: deleteItem.value.filename
        })
      }
    )
    
    if (!response.ok) throw new Error('删除失败')
    
    showMessage('删除成功', 'alert-success')
    deleteItem.value = null
    await loadData()
  } catch (error) {
    console.error('删除失败:', error)
    showMessage('删除失败', 'alert-error')
  }
}

// 导出数据
const exportData = () => {
  if (filteredData.value.length === 0) {
    showMessage('没有可导出的数据', 'alert-warning')
    return
  }
  
  const data = filteredData.value.map(item => ({
    文件名: item.filename,
    视频来源: item.video_filename || '未知',
    标注数量: item.annotation_count || 0,
    类名: (item.class_names || []).join(', '),
    创建时间: formatDate(item.created_at)
  }))
  
  const csv = [
    Object.keys(data[0]!).join(','),
    ...data.map(row => Object.values(row).join(','))
  ].join('\n')
  
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `数据导出_${new Date().toISOString().split('T')[0]}.csv`
  link.click()
  
  showMessage('导出成功', 'alert-success')
}

// 显示消息
const showMessage = (msg: string, type: string = 'alert-info') => {
  message.value = msg
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 3000)
}

// 监听筛选变化，重置到第一页
watch(filters, () => {
  currentPage.value = 1
}, { deep: true })

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
@use '@/styles/glassmorphism.scss';

.page-container-fixed {
  width: 100%;
  height: 100vh;
  background: linear-gradient(135deg, #e0f2fe 0%, #ddd6fe 100%);
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table {
  :deep(th) {
    font-weight: 600;
    font-size: 0.875rem;
  }
}
</style>
