<template>
  <div class="class-group-manager flex flex-col h-full min-h-0">
    <!-- 类名组选择器 -->
    <div class="mb-4 flex-shrink-0">
      <label class="text-sm font-semibold mb-2 block">选择类名组</label>
      <select
        v-model="selectedGroupId"
        @change="onGroupChange"
        class="select select-bordered select-sm w-full"
      >
        <option :value="null" disabled>请选择类名组</option>
        <option v-for="group in groups" :key="group.id" :value="group.id">
          {{ group.name }} ({{ group.classCount || 0 }}个类名)
        </option>
      </select>
    </div>

    <!-- 类名组管理按钮 -->
    <div class="flex gap-2 mb-4 flex-shrink-0">
      <button @click="showCreateGroupModal = true" class="btn btn-xs btn-outline flex-1">
        ➕ 新建组
      </button>
      <button
        v-if="selectedGroupId"
        @click="showEditGroupModal = true"
        class="btn btn-xs btn-outline flex-1"
      >
        ✏️ 编辑组
      </button>
      <button v-if="selectedGroupId" @click="deleteGroup" class="btn btn-xs btn-error btn-outline">
        🗑️
      </button>
    </div>

    <!-- 类名列表 (可滚动区域) -->
    <div class="flex-1 overflow-y-auto space-y-2 mb-3 min-h-0">
      <div
        v-for="cls in currentClasses"
        :key="cls.id"
        :class="[
          'flex items-center justify-between p-2 rounded-lg cursor-pointer transition-all',
          selectedClassId === cls.id
            ? 'bg-primary text-primary-content'
            : 'bg-base-100 hover:bg-base-300',
        ]"
        @click="$emit('select-class', cls.id)"
      >
        <div class="flex items-center gap-2 flex-1 min-w-0">
          <div
            class="w-4 h-4 rounded-full flex-shrink-0"
            :style="{ backgroundColor: cls.color }"
          ></div>
          <span class="text-sm truncate">{{ cls.name }}</span>
        </div>
        <span class="text-xs opacity-60 mr-2 flex-shrink-0">{{ cls.name_en }}</span>
        <button
          @click.stop="editClass(cls)"
          class="btn btn-xs btn-ghost btn-circle flex-shrink-0"
          title="编辑类名"
        >
          ✏️
        </button>
        <button
          @click.stop="removeClass(cls.id)"
          class="btn btn-xs btn-ghost btn-circle flex-shrink-0"
          title="从组中移除"
        >
          ✕
        </button>
      </div>

      <div v-if="currentClasses.length === 0" class="text-center py-4 text-base-content/60">
        <p class="text-xs">该组暂无类名</p>
      </div>
    </div>

    <!-- 添加类名到组 -->
    <div v-if="selectedGroupId && !showAddClassForm" class="mb-2 flex-shrink-0">
      <button
        @click="
          () => {
            initNewClass()
            showAddClassForm = true
          }
        "
        class="btn btn-xs btn-outline w-full"
      >
        ➕ 添加类名
      </button>
    </div>

    <div v-if="showAddClassForm" class="space-y-2 mb-2 flex-shrink-0">
      <input
        v-model="newClassName"
        type="text"
        placeholder="输入中文类名..."
        class="input input-sm input-bordered w-full"
        @keyup.enter="focusEnglishName"
      />
      <input
        v-model="newClassNameEn"
        ref="englishNameInput"
        type="text"
        placeholder="输入英文类名 (用于YOLO训练)..."
        class="input input-sm input-bordered w-full"
        @keyup.enter="addNewClass"
        @keyup.escape="cancelAddClass"
      />
      <div class="flex gap-2">
        <input
          v-model="newClassColor"
          type="color"
          class="w-8 h-8 rounded cursor-pointer"
          title="选择颜色"
        />
        <button @click="addNewClass" class="btn btn-xs btn-success flex-1">创建并添加</button>
        <button @click="cancelAddClass" class="btn btn-xs btn-ghost">取消</button>
      </div>
    </div>

    <!-- 创建类名组模态框 -->
    <div v-if="showCreateGroupModal" class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">创建类名组</h3>
        <div class="space-y-4">
          <div>
            <label class="label">
              <span class="label-text">组名</span>
            </label>
            <input
              v-model="newGroupName"
              type="text"
              placeholder="例如：动物组、车辆组"
              class="input input-bordered w-full"
            />
          </div>
          <div>
            <label class="label">
              <span class="label-text">描述（可选）</span>
            </label>
            <textarea
              v-model="newGroupDescription"
              placeholder="描述这个组的用途..."
              class="textarea textarea-bordered w-full"
              rows="2"
            ></textarea>
          </div>
        </div>
        <div class="modal-action">
          <button @click="createGroup" class="btn btn-primary">创建</button>
          <button @click="closeCreateGroupModal" class="btn">取消</button>
        </div>
      </div>
    </div>

    <!-- 编辑类名组模态框 -->
    <div v-if="showEditGroupModal" class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">编辑类名组</h3>
        <div class="space-y-4">
          <div>
            <label class="label">
              <span class="label-text">组名</span>
            </label>
            <input v-model="editGroupName" type="text" class="input input-bordered w-full" />
          </div>
          <div>
            <label class="label">
              <span class="label-text">描述</span>
            </label>
            <textarea
              v-model="editGroupDescription"
              class="textarea textarea-bordered w-full"
              rows="2"
            ></textarea>
          </div>
        </div>
        <div class="modal-action">
          <button @click="updateGroup" class="btn btn-primary">保存</button>
          <button @click="showEditGroupModal = false" class="btn">取消</button>
        </div>
      </div>
    </div>

    <!-- 删除类名组确认对话框 -->
    <div v-if="showDeleteGroupModal" class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">⚠️ 确认删除</h3>
        <p class="py-4">确定要删除这个类名组吗？此操作无法撤销。</p>
        <div class="modal-action">
          <button @click="confirmDeleteGroup" class="btn btn-error">删除</button>
          <button @click="showDeleteGroupModal = false" class="btn">取消</button>
        </div>
      </div>
    </div>

    <!-- 移除类名确认对话框 -->
    <div v-if="showRemoveClassModal" class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">⚠️ 确认移除</h3>
        <p class="py-4">确定要从组中移除这个类名吗？</p>
        <div class="modal-action">
          <button @click="confirmRemoveClass" class="btn btn-warning">移除</button>
          <button
            @click="
              () => {
                showRemoveClassModal = false
                classToRemove = null
              }
            "
            class="btn"
          >
            取消
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑类名模态框 -->
    <div v-if="showEditClassModal" class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">编辑类名</h3>
        <div class="space-y-4">
          <div>
            <label class="label">
              <span class="label-text">中文类名</span>
            </label>
            <input
              v-model="editClassName"
              type="text"
              placeholder="输入中文类名..."
              class="input input-bordered w-full"
            />
          </div>
          <div>
            <label class="label">
              <span class="label-text">英文类名</span>
            </label>
            <input
              v-model="editClassNameEn"
              type="text"
              placeholder="输入英文类名..."
              class="input input-bordered w-full"
            />
          </div>
          <div>
            <label class="label">
              <span class="label-text">颜色</span>
            </label>
            <div class="flex gap-2 items-center">
              <input
                v-model="editClassColor"
                type="color"
                class="w-12 h-12 rounded cursor-pointer"
              />
              <span class="text-sm opacity-60">{{ editClassColor }}</span>
            </div>
          </div>
        </div>
        <div class="modal-action">
          <button @click="saveEditClass" class="btn btn-primary">保存</button>
          <button @click="closeEditClassModal" class="btn">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import axios from 'axios'

interface ClassGroup {
  id: number
  name: string
  description: string
  created_at: number
  classCount?: number
}

interface Class {
  id: number
  name: string
  name_en: string
  color: string
  order?: number
}

const props = defineProps<{
  selectedClassId: number | null
}>()

const emit = defineEmits<{
  'select-class': [classId: number]
  'group-changed': [groupId: number | null, classes: Class[]]
  'show-message': [message: string, type: 'info' | 'success' | 'error']
  'class-added': []
}>()

const groups = ref<ClassGroup[]>([])
const selectedGroupId = ref<number | null>(null)
const currentClasses = ref<Class[]>([])

const showCreateGroupModal = ref(false)
const showEditGroupModal = ref(false)
const showAddClassForm = ref(false)
const showDeleteGroupModal = ref(false)
const showRemoveClassModal = ref(false)
const showEditClassModal = ref(false)
const classToRemove = ref<number | null>(null)
const editingClassId = ref<number | null>(null)

const newGroupName = ref('')
const newGroupDescription = ref('')
const editGroupName = ref('')
const editGroupDescription = ref('')

const newClassName = ref('')
const newClassNameEn = ref('')
const newClassColor = ref('#00ff00')
const englishNameInput = ref<HTMLInputElement>()

const editClassName = ref('')
const editClassNameEn = ref('')
const editClassColor = ref('#00ff00')

// 预设颜色列表
const colorPalette = [
  '#ef4444', // 红色
  '#f97316', // 橙色
  '#f59e0b', // 黄色
  '#84cc16', // 黄绿色
  '#22c55e', // 绿色
  '#14b8a6', // 青色
  '#06b6d4', // 天蓝色
  '#3b82f6', // 蓝色
  '#6366f1', // 靛蓝色
  '#8b5cf6', // 紫色
  '#ec4899', // 粉色
  '#f43f5e', // 玫红色
]

// 获取随机颜色
const getRandomColor = () => {
  return colorPalette[Math.floor(Math.random() * colorPalette.length)]
}

// 初始化时使用随机颜色
const initNewClass = () => {
  newClassName.value = ''
  newClassNameEn.value = ''
  newClassColor.value = getRandomColor()
}

// 聚焦到英文名输入框
const focusEnglishName = () => {
  if (englishNameInput.value) {
    englishNameInput.value.focus()
  }
}

// 加载所有类名组
const loadGroups = async () => {
  try {
    const response = await axios.get('/api/class-groups')
    groups.value = response.data.groups

    // 为每个组加载类名数量
    for (const group of groups.value) {
      try {
        const classResponse = await axios.get(`/api/class-groups/${group.id}/classes`)
        group.classCount = classResponse.data.classes.length
      } catch (error) {
        console.error(`加载组 ${group.id} 的类名数量失败:`, error)
        group.classCount = 0
      }
    }
  } catch (error) {
    console.error('加载类名组失败:', error)
    emit('show-message', '加载类名组失败', 'error')
  }
}

// 加载选中组的类名
const loadGroupClasses = async () => {
  if (!selectedGroupId.value) {
    currentClasses.value = []
    return
  }

  try {
    const response = await axios.get(`/api/class-groups/${selectedGroupId.value}/classes`)
    currentClasses.value = response.data.classes
  } catch (error) {
    console.error('加载类名失败:', error)
    emit('show-message', '加载类名失败', 'error')
  }
}

// 创建类名组
const createGroup = async () => {
  if (!newGroupName.value.trim()) {
    emit('show-message', '组名不能为空', 'error')
    return
  }

  try {
    const response = await axios.post('/api/class-groups', {
      name: newGroupName.value.trim(),
      description: newGroupDescription.value.trim(),
    })

    emit('show-message', '类名组创建成功', 'success')
    closeCreateGroupModal()
    await loadGroups()

    // 自动选中新创建的组
    selectedGroupId.value = response.data.group.id
    onGroupChange()
  } catch (error: any) {
    console.error('创建类名组失败:', error)
    emit('show-message', error.response?.data?.detail || '创建类名组失败', 'error')
  }
}

// 显示删除组确认对话框
const deleteGroup = () => {
  if (!selectedGroupId.value) return
  showDeleteGroupModal.value = true
}

// 确认删除类名组
const confirmDeleteGroup = async () => {
  if (!selectedGroupId.value) return

  try {
    await axios.delete(`/api/class-groups/${selectedGroupId.value}`)

    emit('show-message', '类名组删除成功', 'success')
    showDeleteGroupModal.value = false
    selectedGroupId.value = null
    currentClasses.value = []
    emit('group-changed', null, [])
    await loadGroups()
  } catch (error) {
    console.error('删除类名组失败:', error)
    emit('show-message', '删除类名组失败', 'error')
    showDeleteGroupModal.value = false
  }
}

// 添加新类名并加入组
const addNewClass = async () => {
  if (!newClassName.value.trim()) {
    emit('show-message', '中文类名不能为空', 'error')
    return
  }

  if (!newClassNameEn.value.trim()) {
    emit('show-message', '英文类名不能为空', 'error')
    return
  }

  if (!selectedGroupId.value) {
    emit('show-message', '请先选择类名组', 'error')
    return
  }

  try {
    // 创建类名
    await axios.post('/api/classes', {
      name: newClassName.value.trim(),
      name_en: newClassNameEn.value.trim(),
      color: newClassColor.value,
      group_id: selectedGroupId.value,
    })

    emit('show-message', '类名创建成功', 'success')
    cancelAddClass()
    await loadGroupClasses()
    await loadGroups()

    // 通知父组件重新加载类名列表
    emit('group-changed', selectedGroupId.value, currentClasses.value)
    emit('class-added')
  } catch (error: any) {
    console.error('创建类名失败:', error)
    emit('show-message', error.response?.data?.detail || '创建类名失败', 'error')
  }
}

// 编辑类名
const editClass = (cls: Class) => {
  editingClassId.value = cls.id
  editClassName.value = cls.name
  editClassNameEn.value = cls.name_en
  editClassColor.value = cls.color
  showEditClassModal.value = true
}

// 保存编辑的类名
const saveEditClass = async () => {
  if (!editClassName.value.trim()) {
    emit('show-message', '中文类名不能为空', 'error')
    return
  }

  if (!editClassNameEn.value.trim()) {
    emit('show-message', '英文类名不能为空', 'error')
    return
  }

  if (!editingClassId.value) return

  try {
    await axios.put(`/api/classes/${editingClassId.value}`, {
      name: editClassName.value.trim(),
      name_en: editClassNameEn.value.trim(),
      color: editClassColor.value,
    })

    emit('show-message', '类名更新成功', 'success')
    closeEditClassModal()
    await loadGroupClasses()
    await loadGroups()

    // 通知父组件重新加载类名列表
    emit('group-changed', selectedGroupId.value, currentClasses.value)
  } catch (error: any) {
    console.error('更新类名失败:', error)
    emit('show-message', error.response?.data?.detail || '更新类名失败', 'error')
  }
}

// 关闭编辑类名模态框
const closeEditClassModal = () => {
  showEditClassModal.value = false
  editingClassId.value = null
  editClassName.value = ''
  editClassNameEn.value = ''
  editClassColor.value = '#00ff00'
}

// 显示移除类名确认对话框
const removeClass = (classId: number) => {
  if (!selectedGroupId.value) return
  classToRemove.value = classId
  showRemoveClassModal.value = true
}

// 确认从组中移除类名
const confirmRemoveClass = async () => {
  if (!selectedGroupId.value || !classToRemove.value) return

  try {
    await axios.delete(`/api/class-groups/${selectedGroupId.value}/classes/${classToRemove.value}`)

    emit('show-message', '类名已从组中移除', 'success')
    showRemoveClassModal.value = false
    classToRemove.value = null
    await loadGroupClasses()
    await loadGroups()
  } catch (error) {
    console.error('移除类名失败:', error)
    emit('show-message', '移除类名失败', 'error')
    showRemoveClassModal.value = false
    classToRemove.value = null
  }
}

// 更新类名组
const updateGroup = async () => {
  if (!selectedGroupId.value || !editGroupName.value.trim()) {
    emit('show-message', '组名不能为空', 'error')
    return
  }

  try {
    await axios.put(`/api/class-groups/${selectedGroupId.value}`, {
      name: editGroupName.value.trim(),
      description: editGroupDescription.value.trim(),
    })

    emit('show-message', '类名组更新成功', 'success')
    showEditGroupModal.value = false
    await loadGroups()
  } catch (error: any) {
    console.error('更新类名组失败:', error)
    emit('show-message', error.response?.data?.detail || '更新类名组失败', 'error')
  }
}

const onGroupChange = async () => {
  await loadGroupClasses()
  emit('group-changed', selectedGroupId.value, currentClasses.value)

  // 加载当前组信息用于编辑
  const currentGroup = groups.value.find((g) => g.id === selectedGroupId.value)
  if (currentGroup) {
    editGroupName.value = currentGroup.name
    editGroupDescription.value = currentGroup.description || ''
  }
}

const closeCreateGroupModal = () => {
  showCreateGroupModal.value = false
  newGroupName.value = ''
  newGroupDescription.value = ''
}

const cancelAddClass = () => {
  showAddClassForm.value = false
  newClassName.value = ''
  newClassNameEn.value = ''
  newClassColor.value = '#00ff00'
}

onMounted(() => {
  loadGroups()
})
</script>

<style scoped lang="scss">
@use '@/styles/glassmorphism.scss';

.class-group-manager {
  /* Styles handled by Tailwind */
}
</style>
