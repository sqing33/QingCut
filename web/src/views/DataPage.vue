<template>
  <div class="page-container-fixed">
    <!-- 顶部筛选栏 -->
    <div
      class="glass-panel rounded-2xl shadow-xl p-6 mb-6 flex-shrink-0"
      style="position: relative; z-index: 10"
    >
      <div class="flex items-center justify-between gap-4">
        <h2 class="text-2xl font-bold flex-shrink-0">📊 数据管理</h2>

        <!-- 筛选条件 -->
        <div class="flex items-center gap-4 flex-1">
          <!-- 视频筛选（多选） -->
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold whitespace-nowrap">🎬 视频</span>
            <div class="dropdown dropdown-bottom">
              <label tabindex="0" class="btn btn-sm w-36 justify-between">
                <span class="truncate">
                  {{
                    selectedVideos.length === 0
                      ? '全部视频'
                      : selectedVideos.length === 1
                        ? selectedVideos[0]
                        : `已选 ${selectedVideos.length} 个视频`
                  }}
                </span>
                <span>▼</span>
              </label>
              <div
                tabindex="0"
                class="dropdown-content z-[100] menu p-2 shadow bg-base-100 rounded-box w-36 mt-2 max-h-60 overflow-y-auto"
              >
                <li>
                  <label class="label cursor-pointer justify-start gap-2">
                    <input
                      type="checkbox"
                      class="checkbox checkbox-sm"
                      :checked="selectedVideos.length === 0"
                      @change="clearVideoSelection"
                    />
                    <span>全部视频</span>
                  </label>
                </li>
                <li v-for="video in videos" :key="video">
                  <label class="label cursor-pointer justify-start gap-2">
                    <input
                      type="checkbox"
                      class="checkbox checkbox-sm"
                      :checked="selectedVideos.includes(video)"
                      @change="toggleVideoSelection(video)"
                    />
                    <span class="truncate">{{ video }}</span>
                  </label>
                </li>
              </div>
            </div>
          </div>

          <!-- 类名筛选 -->
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold whitespace-nowrap">🏷️ 类名</span>
            <select v-model="filters.className" class="select select-bordered select-sm w-32">
              <option value="">全部类名</option>
              <option v-for="cls in classes" :key="cls.id" :value="cls.name">
                {{ cls.name }}
              </option>
            </select>
          </div>

          <!-- 日期范围 -->
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold whitespace-nowrap">📅 日期范围</span>
            <select v-model="filters.dateRange" class="select select-bordered select-sm w-32">
              <option value="">全部时间</option>
              <option value="today">今天</option>
              <option value="week">最近一周</option>
              <option value="month">最近一个月</option>
            </select>
          </div>

          <!-- 数据集筛选 -->
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold whitespace-nowrap">📁 数据集</span>
            <select
              v-model="filters.datasetIdentifier"
              class="select select-bordered select-sm w-32"
            >
              <option value="">全部数据集</option>
              <option value="unassigned">未分配</option>
              <option
                v-for="dataset in existingDatasets"
                :key="dataset.identifier"
                :value="dataset.identifier"
              >
                {{ dataset.name }}
              </option>
            </select>
          </div>

          <!-- 搜索 -->
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold whitespace-nowrap">🔍 搜索</span>
            <input
              v-model="filters.search"
              type="text"
              placeholder="搜索文件名..."
              class="input input-bordered input-sm w-40"
            />
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="flex gap-2 flex-shrink-0">
          <button @click="loadData" class="btn btn-sm btn-ghost" title="刷新">🔄 刷新</button>
          <button @click="downloadExportModal = true" class="btn btn-sm btn-primary">
            📥 导出数据集
          </button>
          <button @click="showYoloExportModal = true" class="btn btn-sm btn-success">
            🎯 转换YOLO数据集
          </button>
          <button @click="showEditDatasetModal = true" class="btn btn-sm btn-info">
            ⚙️ 管理数据集
          </button>
        </div>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div
      v-if="selectedItems.length > 0"
      class="glass-panel rounded-2xl shadow-xl p-4 mb-4 flex-shrink-0"
      style="position: relative; z-index: 9"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <span class="font-semibold">已选择 {{ selectedItems.length }} 张图片</span>
          <button @click="selectedItems = []" class="btn btn-xs btn-ghost">取消选择</button>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-sm font-semibold">分配到数据集：</span>
          <select v-model="batchAssignDataset" class="select select-bordered select-sm w-48">
            <option value="">-- 选择数据集 --</option>
            <option
              v-for="dataset in existingDatasets"
              :key="dataset.identifier"
              :value="dataset.identifier"
            >
              {{ dataset.name }}
            </option>
          </select>
          <button
            @click="handleBatchAssign"
            class="btn btn-sm btn-primary"
            :disabled="!batchAssignDataset || batchAssigning"
          >
            <span v-if="batchAssigning" class="loading loading-spinner loading-xs"></span>
            <span v-else>批量分配</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div
      class="glass-panel rounded-2xl shadow-xl overflow-hidden flex-1 flex flex-col"
      style="position: relative; z-index: 1"
    >
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
              <th>数据集</th>
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
            <tr v-else v-for="item in paginatedData" :key="item.filename" class="hover">
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
                  <div
                    class="mask mask-squircle w-16 h-16 cursor-pointer"
                    @click="previewImage(item)"
                  >
                    <img :src="`${item.path}`" :alt="item.filename" class="object-cover" />
                  </div>
                </div>
              </td>
              <td>
                <div class="font-medium truncate max-w-xs" :title="item.filename">
                  {{ item.filename }}
                </div>
              </td>
              <td>
                <div
                  class="badge badge-ghost truncate max-w-xs"
                  :title="item.video_filename || '未知'"
                >
                  {{ item.video_filename || '未知' }}
                </div>
              </td>
              <td>
                <div v-if="item.datasets && item.datasets.length > 0" class="flex flex-wrap gap-1">
                  <span
                    v-for="dataset in item.datasets"
                    :key="dataset.identifier"
                    class="badge badge-info badge-sm"
                  >
                    {{ dataset.name }}
                  </span>
                </div>
                <span v-else class="text-base-content/40 text-xs">未分配</span>
              </td>
              <td>
                <div class="badge badge-primary">{{ item.annotation_count || 0 }} 个</div>
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
                  <span
                    v-if="!item.class_names || item.class_names.length === 0"
                    class="text-base-content/40"
                  >
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
                  <button @click="previewImage(item)" class="btn btn-xs btn-ghost" title="预览">
                    👁️
                  </button>
                  <button @click="downloadImage(item)" class="btn btn-xs btn-ghost" title="下载">
                    📥
                  </button>
                  <button
                    @click="editDatasets(item)"
                    class="btn btn-xs btn-ghost"
                    title="编辑数据集"
                  >
                    ✏️
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
          <button class="join-item btn btn-sm" :disabled="currentPage === 1" @click="currentPage--">
            «
          </button>
          <button class="join-item btn btn-sm">第 {{ currentPage }} / {{ totalPages }} 页</button>
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

    <!-- YOLO数据集转换模态框 -->
    <div v-if="showYoloExportModal" class="modal modal-open">
      <div class="yolo-modal-box">
        <!-- 标题栏 -->
        <div class="modal-header">
          <div class="flex items-center justify-between w-full">
            <h3 class="text-xl font-bold flex items-center gap-2">
              <span class="text-3xl">🎯</span>
              <span>转换YOLO训练数据集</span>
            </h3>
            <div class="text-sm opacity-80">
              将从选中的
              <span class="font-bold text-primary">{{ selectedVideos.length || '全部' }}</span>
              个视频中提取带标注的图片
            </div>
          </div>
        </div>

        <!-- 内容区域 -->
        <div class="modal-content">
          <!-- 模式选择卡片 -->
          <div class="mode-selector">
            <label
              class="mode-option"
              :class="{ 'mode-option-active': yoloExportForm.mode === 'new' }"
              @click="yoloExportForm.mode = 'new'"
            >
              <div class="mode-content">
                <div class="mode-icon">🆕</div>
                <div>
                  <div class="font-semibold">创建新数据集</div>
                  <div class="text-xs opacity-70">创建全新的训练数据集</div>
                </div>
              </div>
            </label>

            <label
              class="mode-option"
              :class="{ 'mode-option-active': yoloExportForm.mode === 'append' }"
              @click="yoloExportForm.mode = 'append'"
            >
              <div class="mode-content">
                <div class="mode-icon">➕</div>
                <div>
                  <div class="font-semibold">追加到现有数据集</div>
                  <div class="text-xs opacity-70">向已有数据集添加更多图片</div>
                </div>
              </div>
            </label>
          </div>

          <!-- 表单区域 -->
          <div class="form-area">
            <!-- 新建模式表单 -->
            <div v-if="yoloExportForm.mode === 'new'" class="form-content">
              <div class="form-group">
                <label class="form-label">
                  <span class="label-icon">📝</span>
                  <span>数据集名称</span>
                  <span class="label-hint">（中文）</span>
                </label>
                <input
                  v-model="yoloExportForm.name"
                  type="text"
                  placeholder="例如：猫狗识别数据集"
                  class="input input-bordered w-full"
                />
              </div>

              <div class="form-group">
                <label class="form-label">
                  <span class="label-icon">🔤</span>
                  <span>英文标识符</span>
                  <span class="label-hint">（用于文件夹名）</span>
                </label>
                <input
                  v-model="yoloExportForm.identifier"
                  type="text"
                  placeholder="例如：cat_dog_dataset"
                  class="input input-bordered w-full"
                  pattern="[a-zA-Z0-9_]+"
                />
                <div class="form-hint">
                  <span class="opacity-60">保存路径：</span>
                  <code class="text-primary"
                    >server/dataset/{{ yoloExportForm.identifier || '{标识符}' }}/</code
                  >
                </div>
              </div>
            </div>

            <!-- 追加模式表单 -->
            <div v-else class="form-content">
              <div class="form-group">
                <label class="form-label">
                  <span class="label-icon">📁</span>
                  <span>选择现有数据集</span>
                </label>
                <select
                  v-model="yoloExportForm.existingDataset"
                  class="select select-bordered w-full"
                >
                  <option value="">-- 请选择要追加的数据集 --</option>
                  <option
                    v-for="dataset in existingDatasets"
                    :key="dataset.identifier"
                    :value="dataset.identifier"
                  >
                    <template
                      v-if="dataset.train_images !== undefined && dataset.val_images !== undefined"
                    >
                      {{ dataset.name }} ({{ dataset.total_images }} 张: 训练{{
                        dataset.train_images
                      }}
                      验证{{ dataset.val_images }})
                    </template>
                    <template v-else>
                      {{ dataset.name }} ({{ dataset.image_count }} 张图片)
                    </template>
                  </option>
                </select>
                <div class="form-hint" v-if="yoloExportForm.existingDataset">
                  <span class="opacity-60">追加到：</span>
                  <code class="text-primary"
                    >server/dataset/{{ yoloExportForm.existingDataset }}/</code
                  >
                </div>
              </div>
            </div>
          </div>

          <!-- 统计信息卡片 -->
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon text-primary">📷</div>
              <div class="stat-content">
                <div class="stat-label">待添加图片</div>
                <div class="stat-value text-primary">{{ getExportFrameCount() }}</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon text-secondary">🏷️</div>
              <div class="stat-content">
                <div class="stat-label">待添加标注</div>
                <div class="stat-value text-secondary">{{ getExportAnnotationCount() }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部按钮栏 -->
        <div class="modal-footer">
          <button
            @click="
              () => {
                showYoloExportModal = false
                yoloExportForm.name = ''
                yoloExportForm.identifier = ''
                yoloExportForm.mode = 'new'
                yoloExportForm.existingDataset = ''
              }
            "
            class="btn btn-ghost"
            :disabled="yoloExporting"
          >
            取消
          </button>
          <button
            @click="handleYoloExport"
            class="btn btn-success min-w-[140px]"
            :disabled="
              (yoloExportForm.mode === 'new' &&
                (!yoloExportForm.name || !yoloExportForm.identifier)) ||
              (yoloExportForm.mode === 'append' && !yoloExportForm.existingDataset) ||
              yoloExporting
            "
          >
            <span v-if="yoloExporting" class="loading loading-spinner loading-sm"></span>
            <span v-else>{{
              yoloExportForm.mode === 'new' ? '🚀 创建数据集' : '➕ 追加图片'
            }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑数据集模态框 -->
    <div v-if="editItem" class="modal modal-open">
      <div class="modal-box max-w-md">
        <h3 class="font-bold text-lg mb-4">✏️ 编辑数据集归属</h3>
        <div class="mb-4">
          <div class="text-sm opacity-70 mb-2">图片：{{ editItem.filename }}</div>
        </div>

        <!-- 数据集多选列表 -->
        <div class="form-control">
          <label class="label">
            <span class="label-text font-semibold">选择数据集</span>
          </label>
          <div class="max-h-60 overflow-y-auto border border-base-300 rounded-lg p-3 space-y-2">
            <label
              v-for="dataset in existingDatasets"
              :key="dataset.identifier"
              class="flex items-center gap-3 p-2 hover:bg-base-200 rounded-lg cursor-pointer transition-colors"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-sm checkbox-primary"
                :value="dataset.identifier"
                v-model="editSelectedDatasets"
              />
              <div class="flex-1">
                <div class="font-medium">{{ dataset.name }}</div>
                <div class="text-xs opacity-60">
                  {{ dataset.identifier }} ({{ dataset.image_count }} 张)
                </div>
              </div>
            </label>
            <div v-if="existingDatasets.length === 0" class="text-center py-4 text-base-content/40">
              暂无数据集，请先创建数据集
            </div>
          </div>
        </div>

        <div class="modal-action">
          <button @click="handleSaveDatasets" class="btn btn-primary" :disabled="editSaving">
            <span v-if="editSaving" class="loading loading-spinner loading-xs"></span>
            <span v-else>保存</span>
          </button>
          <button
            @click="
              () => {
                editItem = null
                editSelectedDatasets = []
              }
            "
            class="btn"
          >
            取消
          </button>
        </div>
      </div>
    </div>

    <!-- 管理数据集模态框 -->
    <div v-if="showEditDatasetModal" class="modal modal-open">
      <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-lg mb-4">⚙️ 管理数据集</h3>

        <div v-if="existingDatasets.length === 0" class="text-center py-8 text-base-content/40">
          <div class="text-4xl mb-2">📭</div>
          <p>暂无数据集</p>
        </div>

        <div v-else class="space-y-3 max-h-96 overflow-y-auto">
          <div
            v-for="dataset in existingDatasets"
            :key="dataset.identifier"
            class="glass-panel p-4 rounded-lg"
          >
            <div class="flex items-center gap-4">
              <div class="flex-1">
                <div v-if="editingDatasetIdentifier === dataset.identifier" class="space-y-2">
                  <input
                    v-model="editingDatasetName"
                    type="text"
                    class="input input-bordered w-full"
                    placeholder="输入新的数据集名称"
                    @keyup.enter="handleSaveDatasetName"
                  />
                  <div class="flex gap-2">
                    <button
                      @click="handleSaveDatasetName"
                      class="btn btn-sm btn-primary"
                      :disabled="savingDataset || !editingDatasetName"
                    >
                      <span v-if="savingDataset" class="loading loading-spinner loading-xs"></span>
                      <span v-else>💾 保存</span>
                    </button>
                    <button
                      @click="
                        () => {
                          editingDatasetIdentifier = ''
                          editingDatasetName = ''
                        }
                      "
                      class="btn btn-sm btn-ghost"
                      :disabled="savingDataset"
                    >
                      取消
                    </button>
                  </div>
                </div>
                <div v-else>
                  <div class="font-semibold text-lg">{{ dataset.name }}</div>
                  <div
                    v-if="dataset.train_images !== undefined && dataset.val_images !== undefined"
                    class="text-sm opacity-60"
                  >
                    {{ dataset.identifier }} ({{ dataset.total_images }} 张: 训练{{
                      dataset.train_images
                    }}
                    验证{{ dataset.val_images }})
                  </div>
                  <div v-else class="text-sm opacity-60">
                    {{ dataset.identifier }} ({{ dataset.image_count }} 张图片)
                  </div>
                </div>
              </div>
              <div v-if="editingDatasetIdentifier !== dataset.identifier" class="flex gap-2">
                <button
                  @click="handleEditDataset(dataset.identifier)"
                  class="btn btn-sm btn-ghost"
                  title="编辑名称"
                >
                  ✏️
                </button>
                <button
                  @click="showDeleteConfirm(dataset.identifier)"
                  class="btn btn-sm btn-error btn-ghost"
                  title="删除数据集"
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-action">
          <button
            @click="
              () => {
                showEditDatasetModal = false
                editingDatasetIdentifier = ''
                editingDatasetName = ''
              }
            "
            class="btn"
          >
            关闭
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteConfirmModal" class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg">⚠️ 确认删除</h3>
        <p class="py-4">
          确定要删除数据集 "<strong>{{
            existingDatasets.find((d) => d.identifier === deletingDatasetIdentifier)?.name
          }}</strong
          >" 吗？ <br /><br />
          <span class="text-error"
            >此操作将删除数据集目录中的所有文件（包括
            {{
              existingDatasets.find((d) => d.identifier === deletingDatasetIdentifier)?.image_count
            }}
            张图片和标签文件），且无法恢复！</span
          >
        </p>
        <div class="modal-action">
          <button @click="confirmDeleteDataset" class="btn btn-error" :disabled="deletingDataset">
            <span v-if="deletingDataset" class="loading loading-spinner loading-xs"></span>
            <span v-else>确认删除</span>
          </button>
          <button
            @click="
              () => {
                showDeleteConfirmModal = false
                deletingDatasetIdentifier = ''
              }
            "
            class="btn"
            :disabled="deletingDataset"
          >
            取消
          </button>
        </div>
      </div>
    </div>

    <!-- 导出数据模态框 -->
    <div v-if="downloadExportModal" class="modal modal-open">
      <div class="modal-box max-w-md">
        <h3 class="font-bold text-lg mb-6">📥 导出YOLO数据集</h3>

        <div class="space-y-4">
          <div class="form-group">
            <label class="form-label">
              <span class="label-icon">📁</span>
              <span>选择数据集</span>
            </label>
            <select v-model="downloadingDataset" class="select select-bordered w-full">
              <option value="">-- 请选择要导出的数据集 --</option>
              <option
                v-for="dataset in existingDatasets"
                :key="dataset.identifier"
                :value="dataset.identifier"
              >
                <template
                  v-if="dataset.train_images !== undefined && dataset.val_images !== undefined"
                >
                  {{ dataset.name }} ({{ dataset.total_images }} 张: 训练{{
                    dataset.train_images
                  }}
                  验证{{ dataset.val_images }})
                </template>
                <template v-else> {{ dataset.name }} ({{ dataset.image_count }} 张图片) </template>
              </option>
            </select>
          </div>

          <div v-if="downloadingDataset" class="bg-base-200 p-4 rounded-lg text-sm">
            <div class="font-medium mb-2">📦 导出内容说明：</div>
            <ul class="space-y-1 text-xs opacity-80">
              <li>• 处理后的图片文件（填充缩放至640x640）</li>
              <li>• YOLO格式标注文件（.txt）</li>
              <li>• 数据集配置文件（train.yaml）</li>
              <li>• 类名文件（classes.txt）</li>
              <li>• 数据集信息文件</li>
            </ul>
            <div class="mt-2 text-xs opacity-60">
              结构：<code class="bg-base-300 px-1 py-0.5 rounded"
                >dataset_name/train/ & dataset_name/val/</code
              >
            </div>
          </div>
        </div>

        <div class="modal-action mt-6">
          <button
            @click="
              () => {
                downloadExportModal = false
                downloadingDataset = ''
              }
            "
            class="btn btn-ghost"
          >
            取消
          </button>
          <button
            @click="downloadYoloDataset"
            class="btn btn-primary"
            :disabled="!downloadingDataset"
          >
            <span v-if="downloadingDataset">📥 下载数据集</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 消息提示 -->
    <div v-if="message" class="toast toast-top toast-center" style="z-index: 9999">
      <div :class="['alert', messageType]">
        <span>{{ message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'
import ImagePreviewModal from '@/components/ImagePreviewModal.vue'

interface Frame {
  filename: string
  path: string
  created_at: number
  video_filename?: string
  annotation_count?: number
  class_names?: string[]
  dataset_identifier?: string
  datasets?: Array<{ identifier: string; name: string }>
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
const selectedVideos = ref<string[]>([])
const previewItem = ref<Frame | null>(null)
const previewImageUrl = ref('')
const previewImageInfo = ref<{ filename: string; path: string }>({ filename: '', path: '' })
const previewAnnotations = ref<any[]>([])
const deleteItem = ref<Frame | null>(null)
const message = ref('')
const messageType = ref('alert-info')
const showYoloExportModal = ref(false)
const yoloExportForm = ref({
  name: '',
  identifier: '',
  mode: 'new' as 'new' | 'append',
  existingDataset: '',
})
const yoloExporting = ref(false)
const downloadExportModal = ref(false)
const downloadingDataset = ref('')
const existingDatasets = ref<
  Array<{
    identifier: string
    name: string
    image_count: number
    train_images?: number
    val_images?: number
    total_images?: number
  }>
>([])
const batchAssignDataset = ref('')
const batchAssigning = ref(false)
const editItem = ref<Frame | null>(null)
const editSelectedDatasets = ref<string[]>([])
const editSaving = ref(false)
const showEditDatasetModal = ref(false)
const editingDatasetIdentifier = ref('')
const editingDatasetName = ref('')
const savingDataset = ref(false)
const showDeleteConfirmModal = ref(false)
const deletingDatasetIdentifier = ref('')
const deletingDataset = ref(false)

// 筛选条件
const filters = ref({
  videoFilename: '',
  className: '',
  dateRange: '',
  search: '',
  datasetIdentifier: '',
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 统计信息
const totalCount = computed(() => allData.value.length)
const annotatedCount = computed(
  () => allData.value.filter((item) => item.annotation_count && item.annotation_count > 0).length,
)
const annotationRate = computed(() =>
  totalCount.value > 0 ? Math.round((annotatedCount.value / totalCount.value) * 100) : 0,
)

// 视频多选功能
const toggleVideoSelection = (video: string) => {
  const index = selectedVideos.value.indexOf(video)
  if (index > -1) {
    selectedVideos.value.splice(index, 1)
  } else {
    selectedVideos.value.push(video)
  }
}

const clearVideoSelection = () => {
  selectedVideos.value = []
}

// 筛选数据
const filteredData = computed(() => {
  let data = allData.value

  // 视频筛选（多选）
  if (selectedVideos.value.length > 0) {
    data = data.filter(
      (item) => item.video_filename && selectedVideos.value.includes(item.video_filename),
    )
  }

  // 保持旧的单选筛选逻辑（向后兼容）
  if (filters.value.videoFilename) {
    data = data.filter((item) => item.video_filename === filters.value.videoFilename)
  }

  // 类名筛选
  if (filters.value.className) {
    data = data.filter(
      (item) => item.class_names && item.class_names.includes(filters.value.className),
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
      data = data.filter((item) => item.created_at >= threshold)
    }
  }

  // 数据集筛选
  if (filters.value.datasetIdentifier) {
    if (filters.value.datasetIdentifier === 'unassigned') {
      data = data.filter((item) => !item.dataset_identifier)
    } else {
      data = data.filter((item) => item.dataset_identifier === filters.value.datasetIdentifier)
    }
  }

  // 搜索筛选
  if (filters.value.search) {
    const search = filters.value.search.toLowerCase()
    data = data.filter(
      (item) =>
        item.filename.toLowerCase().includes(search) ||
        (item.video_filename && item.video_filename.toLowerCase().includes(search)),
    )
  }

  return data
})

// 分页数据
const totalPages = computed(() => Math.ceil(filteredData.value.length / pageSize.value))
const startIndex = computed(() => (currentPage.value - 1) * pageSize.value)
const endIndex = computed(() =>
  Math.min(startIndex.value + pageSize.value, filteredData.value.length),
)
const paginatedData = computed(() => filteredData.value.slice(startIndex.value, endIndex.value))

// 全选
const isAllSelected = computed(
  () => selectedItems.value.length > 0 && selectedItems.value.length === paginatedData.value.length,
)

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedItems.value = []
  } else {
    selectedItems.value = paginatedData.value.map((item) => item.filename)
  }
}

// 加载现有数据集列表
const loadExistingDatasets = async () => {
  try {
    const response = await axios.get('/api/datasets')
    existingDatasets.value = response.data.datasets || []
  } catch (error) {
    console.error('加载数据集列表失败:', error)
  }
}

// 加载类名列表
const loadClasses = async () => {
  try {
    const classesResponse = await axios.get('/api/classes')
    classes.value = classesResponse.data.classes || []
  } catch (error) {
    console.error('加载类名列表失败:', error)
  }
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    // 加载截图数据（包含标注信息）
    const framesResponse = await axios.get('/api/frames')
    allData.value = framesResponse.data.frames

    // 提取视频列表
    const videoSet = new Set<string>()
    allData.value.forEach((frame) => {
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
  const cls = classes.value.find((c) => c.name === className)
  return cls ? cls.color : '#3b82f6'
}

// 获取数据集名称
const getDatasetName = (identifier: string) => {
  const dataset = existingDatasets.value.find((d) => d.identifier === identifier)
  return dataset ? dataset.name : identifier
}

// 格式化日期
const formatDate = (timestamp: number) => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 预览图片
const previewImage = async (item: Frame) => {
  previewItem.value = item
  previewImageUrl.value = `${item.path}`
  previewImageInfo.value = {
    filename: item.filename,
    path: item.path,
  }

  // 加载标注数据
  try {
    const response = await axios.get(`/api/frames/${item.filename}/annotations`)
    previewAnnotations.value = response.data.annotations || []
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
    const response = await axios.post(`/api/frames/${previewItem.value.filename}/annotations`, {
      annotations,
    })

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
  link.href = `${item.path}`
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
    const response = await axios.post('/api/delete-frame', {
      filename: deleteItem.value.filename,
    })

    showMessage('删除成功', 'alert-success')
    deleteItem.value = null
    await loadData()
    await loadExistingDatasets() // 重新加载数据集列表，更新统计信息
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

  const data = filteredData.value.map((item) => ({
    文件名: item.filename,
    视频来源: item.video_filename || '未知',
    标注数量: item.annotation_count || 0,
    类名: (item.class_names || []).join(', '),
    创建时间: formatDate(item.created_at),
  }))

  const csv = [
    Object.keys(data[0]!).join(','),
    ...data.map((row) => Object.values(row).join(',')),
  ].join('\n')

  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `数据导出_${new Date().toISOString().split('T')[0]}.csv`
  link.click()

  showMessage('导出成功', 'alert-success')
}

// YOLO导出相关函数
const getExportFrameCount = () => {
  if (selectedVideos.value.length === 0) {
    return allData.value.filter((item) => item.annotation_count && item.annotation_count > 0).length
  }
  return allData.value.filter(
    (item) =>
      item.annotation_count &&
      item.annotation_count > 0 &&
      item.video_filename &&
      selectedVideos.value.includes(item.video_filename),
  ).length
}

const getExportAnnotationCount = () => {
  if (selectedVideos.value.length === 0) {
    return allData.value.reduce((sum, item) => sum + (item.annotation_count || 0), 0)
  }
  return allData.value
    .filter((item) => item.video_filename && selectedVideos.value.includes(item.video_filename))
    .reduce((sum, item) => sum + (item.annotation_count || 0), 0)
}

const handleYoloExport = async () => {
  // 根据模式验证
  if (yoloExportForm.value.mode === 'new') {
    if (!yoloExportForm.value.name || !yoloExportForm.value.identifier) {
      showMessage('请填写完整信息', 'alert-warning')
      return
    }
    // 验证标识符格式
    if (!/^[a-zA-Z0-9_]+$/.test(yoloExportForm.value.identifier)) {
      showMessage('标识符只能包含英文字母、数字和下划线', 'alert-error')
      return
    }
  } else {
    if (!yoloExportForm.value.existingDataset) {
      showMessage('请选择要追加的数据集', 'alert-warning')
      return
    }
  }

  yoloExporting.value = true
  try {
    const requestBody: any = {
      video_filenames: selectedVideos.value.length > 0 ? selectedVideos.value : null,
    }

    if (yoloExportForm.value.mode === 'new') {
      requestBody.name = yoloExportForm.value.name
      requestBody.identifier = yoloExportForm.value.identifier
      requestBody.append_mode = false
    } else {
      // 追加模式：使用现有数据集的标识符
      const dataset = existingDatasets.value.find(
        (d) => d.identifier === yoloExportForm.value.existingDataset,
      )
      requestBody.name = dataset?.name || '未命名数据集'
      requestBody.identifier = yoloExportForm.value.existingDataset
      requestBody.append_mode = true
    }

    const response = await axios.post('/api/export/yolo-dataset', requestBody)
    const result = response.data
    const message =
      yoloExportForm.value.mode === 'new'
        ? `数据集创建成功！共 ${result.total_images} 张图片，${result.total_annotations} 个标注`
        : `数据集更新成功！已添加 ${result.total_images} 张图片，${result.total_annotations} 个标注`

    showMessage(message, 'alert-success')

    // 关闭模态框并重置表单
    showYoloExportModal.value = false
    yoloExportForm.value.name = ''
    yoloExportForm.value.identifier = ''
    yoloExportForm.value.mode = 'new'
    yoloExportForm.value.existingDataset = ''

    // 重新加载数据集列表和表格数据
    await loadExistingDatasets()
    await loadData()
  } catch (error: any) {
    console.error('YOLO导出失败:', error)
    showMessage(
      error.response?.data?.detail || error.message || 'YOLO数据集转换失败',
      'alert-error',
    )
  } finally {
    yoloExporting.value = false
  }
}

// 编辑图片的数据集归属
const editDatasets = (item: Frame) => {
  editItem.value = item
  // 初始化已选中的数据集
  editSelectedDatasets.value = item.datasets?.map((d) => d.identifier) || []
}

// 保存数据集编辑
const handleSaveDatasets = async () => {
  if (!editItem.value) return

  editSaving.value = true
  try {
    const response = await axios.post(`/api/frames/${editItem.value.filename}/datasets`, {
      dataset_identifiers: editSelectedDatasets.value,
    })

    showMessage('数据集归属已更新', 'alert-success')

    // 关闭模态框并重新加载数据
    editItem.value = null
    editSelectedDatasets.value = []
    await loadData()
    await loadExistingDatasets()
  } catch (error: any) {
    console.error('保存数据集失败:', error)
    showMessage(error.response?.data?.detail || error.message || '保存数据集失败', 'alert-error')
  } finally {
    editSaving.value = false
  }
}

// 编辑数据集
const handleEditDataset = (identifier: string) => {
  const dataset = existingDatasets.value.find((d) => d.identifier === identifier)
  if (dataset) {
    editingDatasetIdentifier.value = identifier
    editingDatasetName.value = dataset.name
  }
}

// 保存数据集名称
const handleSaveDatasetName = async () => {
  if (!editingDatasetIdentifier.value || !editingDatasetName.value) {
    showMessage('请填写数据集名称', 'alert-warning')
    return
  }

  savingDataset.value = true
  try {
    const response = await axios.put(`/api/datasets/${editingDatasetIdentifier.value}`, {
      name: editingDatasetName.value,
    })

    const result = response.data
    showMessage(result.message || '数据集名称已更新', 'alert-success')

    // 重置编辑状态
    editingDatasetIdentifier.value = ''
    editingDatasetName.value = ''

    // 重新加载数据集列表
    await loadExistingDatasets()
  } catch (error: any) {
    console.error('保存数据集失败:', error)
    showMessage(error.response?.data?.detail || error.message || '保存数据集失败', 'alert-error')
  } finally {
    savingDataset.value = false
  }
}

// 显示删除确认
const showDeleteConfirm = (identifier: string) => {
  deletingDatasetIdentifier.value = identifier
  showDeleteConfirmModal.value = true
}

// 确认删除数据集
const confirmDeleteDataset = async () => {
  if (!deletingDatasetIdentifier.value) return

  deletingDataset.value = true
  try {
    const response = await axios.delete(`/api/datasets/${deletingDatasetIdentifier.value}`)

    const result = response.data
    showMessage(result.message || '数据集已删除', 'alert-success')

    // 关闭确认对话框并重置
    showDeleteConfirmModal.value = false
    deletingDatasetIdentifier.value = ''

    // 重新加载数据集列表和表格数据
    await loadExistingDatasets()
    await loadData()
  } catch (error: any) {
    console.error('删除数据集失败:', error)
    showMessage(error.response?.data?.detail || error.message || '删除数据集失败', 'alert-error')
  } finally {
    deletingDataset.value = false
  }
}

// 批量分配数据集
const handleBatchAssign = async () => {
  if (!batchAssignDataset.value || selectedItems.value.length === 0) {
    showMessage('请选择数据集和图片', 'alert-warning')
    return
  }

  batchAssigning.value = true
  try {
    const response = await axios.post('/api/frames/batch-assign-dataset', {
      filenames: selectedItems.value,
      dataset_identifier: batchAssignDataset.value,
    })

    const result = response.data
    showMessage(`成功分配 ${result.updated_count} 张图片到数据集`, 'alert-success')

    // 清空选择并重新加载数据
    selectedItems.value = []
    batchAssignDataset.value = ''
    await loadData()
  } catch (error: any) {
    console.error('批量分配失败:', error)
    showMessage(error.response?.data?.detail || error.message || '批量分配失败', 'alert-error')
  } finally {
    batchAssigning.value = false
  }
}

const downloadYoloDataset = async () => {
  if (!downloadingDataset.value) return

  try {
    const response = await axios.get(`/api/export/yolo-dataset-zip/${downloadingDataset.value}`, {
      responseType: 'blob',
    })

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url

    const filename =
      response.headers['content-disposition']?.split("filename*=UTF-8''")[1] || 'dataset.zip'
    link.setAttribute('download', decodeURIComponent(filename))

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    window.URL.revokeObjectURL(url)

    showMessage('数据集导出成功', 'alert-success')

    // 关闭模态框
    downloadExportModal.value = false
    downloadingDataset.value = ''
  } catch (error: any) {
    console.error('导出数据集失败:', error)
    showMessage(error.response?.data?.detail || error.message || '导出数据集失败', 'alert-error')
  }
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
watch(
  filters,
  () => {
    currentPage.value = 1
  },
  { deep: true },
)

onMounted(() => {
  loadData()
  loadExistingDatasets()
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

/* 确保下拉菜单显示在最上层 */
:deep(.dropdown-content) {
  z-index: 1000 !important;
}

/* YOLO模态框样式 */
.yolo-modal-box {
  position: fixed;
  width: 600px;
  height: 680px;
  max-width: 90vw;
  max-height: 85vh;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(250, 250, 255, 0.95) 100%);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.5);
}

.modal-header {
  padding: 24px 28px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  background: linear-gradient(to right, rgba(96, 165, 250, 0.1), rgba(168, 85, 247, 0.1));
  flex-shrink: 0;
}

.modal-content {
  flex: 1;
  padding: 24px 28px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;

  /* 自定义滚动条 */
  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.05);
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(96, 165, 250, 0.5);
    border-radius: 4px;

    &:hover {
      background: rgba(96, 165, 250, 0.7);
    }
  }
}

.modal-footer {
  padding: 20px 28px;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: rgba(248, 250, 252, 0.8);
  flex-shrink: 0;
}

/* 信息卡片 */
.info-card {
  display: flex;
  gap: 16px;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(147, 51, 234, 0.1) 100%);
  border-radius: 16px;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.info-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.info-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 模式选择器 */
.mode-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mode-option {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 16px;
  border: 2px solid rgba(0, 0, 0, 0.1);
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    border-color: rgba(59, 130, 246, 0.5);
    background: rgba(59, 130, 246, 0.05);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.mode-option-active {
    border-color: rgb(59, 130, 246);
    background: rgba(59, 130, 246, 0.1);
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.2);
  }
}

.mode-content {
  display: flex;
  gap: 12px;
  align-items: center;
  flex: 1;
}

.mode-icon {
  font-size: 24px;
  flex-shrink: 0;
}

/* 表单区域 */
.form-area {
  height: 220px;
  display: flex;
  flex-direction: column;
}

.form-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 0.95rem;
}

.label-icon {
  font-size: 18px;
}

.label-hint {
  font-size: 0.85rem;
  font-weight: normal;
  opacity: 0.6;
}

.form-hint {
  font-size: 0.85rem;
  margin-top: 4px;
  padding: 8px 12px;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 8px;
  border-left: 3px solid rgba(59, 130, 246, 0.5);

  code {
    background: rgba(59, 130, 246, 0.1);
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.9em;
  }
}

/* 统计信息网格 */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-card {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: white;
  border-radius: 16px;
  border: 2px solid rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    border-color: rgba(59, 130, 246, 0.3);
  }
}

.stat-icon {
  font-size: 40px;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.85rem;
  opacity: 0.7;
  font-weight: 500;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  line-height: 1;
}
</style>
