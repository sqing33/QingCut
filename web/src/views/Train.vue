<template>
  <div class="train-page">
    <div class="grid grid-cols-1 lg:grid-cols-10 gap-6 h-full">
      <!-- 左侧：创建训练任务 -->
      <div class="glass-panel rounded-2xl shadow-xl p-6 lg:col-span-2 flex flex-col">
        <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span>🚀</span>
          <span>YOLO 模型训练</span>
        </h3>

        <!-- 数据集选择 -->
        <div class="form-control mb-4">
          <label class="label">
            <span class="label-text font-semibold">📁 选择数据集</span>
          </label>
          <select v-model="trainingForm.dataset" class="select select-bordered w-full">
            <option value="">-- 请选择数据集 --</option>
            <option
              v-for="dataset in datasets"
              :key="dataset.identifier"
              :value="dataset.identifier"
            >
              {{ dataset.name }} ({{ dataset.total_images }} 张图片)
            </option>
          </select>
          <!-- 预留数据集信息显示区域 -->
          <div class="mt-2 min-h-[20px] text-sm opacity-70">
            <div v-if="selectedDataset">
              训练集: {{ selectedDataset.train_images }} 张 | 验证集:
              {{ selectedDataset.val_images }} 张
            </div>
          </div>
        </div>

        <!-- 模型选择 -->
        <div class="form-control mb-4">
          <label class="label">
            <span class="label-text font-semibold">🤖 选择预训练模型</span>
          </label>
          <select v-model="trainingForm.model" class="select select-bordered w-full">
            <option value="">-- 请选择模型 --</option>
            <option
              v-for="model in models"
              :key="model.name"
              :value="model.name"
              :disabled="!model.is_local && downloading"
            >
              {{ model.name }}
              <template v-if="model.is_local"> ✓ ({{ model.size }}) </template>
              <template v-else-if="model.is_downloadable"> (可下载) </template>
            </option>
          </select>

          <!-- 操作按钮行 -->
          <div class="mt-2">
            <div class="flex items-center gap-2">
              <!-- 上传按钮 -->
              <button
                @click="triggerFileUpload"
                class="btn btn-sm btn-secondary w-20"
                :disabled="downloading || uploading"
              >
                <span v-if="uploading" class="loading loading-spinner loading-xs"></span>
                <span v-else>📤 上传</span>
              </button>

              <!-- 下载按钮 -->
              <button
                v-if="selectedModel && !selectedModel.is_local && selectedModel.is_downloadable"
                @click="downloadModel(selectedModel.name)"
                class="btn btn-sm btn-primary w-20"
                :disabled="downloading || uploading"
              >
                <span v-if="downloading" class="loading loading-spinner loading-xs"></span>
                <span v-else>⬇️ 下载</span>
              </button>

              <!-- 隐藏的文件选择器 -->
              <input
                ref="fileInput"
                type="file"
                accept=".pt"
                @change="handleFileUpload"
                style="display: none"
              />
            </div>

            <!-- 下载/上传进度条区域 - 预留空间 -->
            <div class="min-h-[60px] mt-2">
              <div v-if="(downloading && downloadProgress) || (uploading && uploadProgress)">
                <progress
                  class="progress progress-primary w-full"
                  :value="uploading ? uploadProgress : downloadProgress?.progress || 0"
                  max="100"
                ></progress>
                <div class="flex items-center justify-between text-xs mt-1 opacity-70">
                  <span>{{ uploading ? '上传中...' : '下载中...' }}</span>
                  <span v-if="downloadProgress && !uploading">
                    {{ formatBytes(downloadProgress.downloaded) }} /
                    {{ formatBytes(downloadProgress.total) }}
                  </span>
                  <span
                    >{{
                      (uploading ? uploadProgress : downloadProgress?.progress || 0).toFixed(1)
                    }}%</span
                  >
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 训练参数 -->
        <div class="space-y-4 mb-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text font-semibold">🔢 训练轮数</span>
            </label>
            <input
              v-model.number="trainingForm.epochs"
              type="number"
              min="1"
              max="1000"
              class="input input-bordered w-full"
            />
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text font-semibold">📦 批次大小</span>
            </label>
            <input
              v-model.number="trainingForm.batchSize"
              type="number"
              min="1"
              max="128"
              class="input input-bordered w-full"
            />
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text font-semibold">🖼️ 图片尺寸</span>
            </label>
            <input
              v-model.number="trainingForm.imageSize"
              type="number"
              min="320"
              max="1280"
              step="32"
              class="input input-bordered w-full"
            />
          </div>
        </div>

        <!-- 开始训练按钮 -->
        <button
          @click="startTraining"
          class="btn btn-primary w-full mt-auto"
          :disabled="!canStartTraining || creating"
        >
          <span v-if="creating" class="loading loading-spinner loading-sm"></span>
          <span v-else>开始训练</span>
        </button>
      </div>

      <!-- 右侧：训练任务列表 -->
      <div class="glass-panel rounded-2xl shadow-xl p-6 lg:col-span-8 flex flex-col">
        <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span>📊</span>
          <span>训练任务列表</span>
        </h3>

        <!-- Filter and Task List -->
        <div v-if="tasks.length === 0" class="text-center py-8 text-base-content/60">
          <div class="text-4xl mb-2">📭</div>
          <p>暂无训练任务</p>
        </div>

        <div v-else>
          <!-- Filter Buttons -->
          <div class="flex gap-2 mb-4 border-b border-base-200 pb-2">
            <button
              @click="filterStatus = 'all'"
              class="btn btn-sm"
              :class="{ 'btn-active': filterStatus === 'all' }"
            >
              全部
            </button>
            <button
              @click="filterStatus = 'running'"
              class="btn btn-sm"
              :class="{ 'btn-active': filterStatus === 'running' }"
            >
              训练中
            </button>
            <button
              @click="filterStatus = 'completed'"
              class="btn btn-sm"
              :class="{ 'btn-active': filterStatus === 'completed' }"
            >
              已完成
            </button>
            <button
              @click="filterStatus = 'failed'"
              class="btn btn-sm"
              :class="{ 'btn-active': filterStatus === 'failed' }"
            >
              失败
            </button>
          </div>

          <div v-if="filteredTasks.length === 0" class="text-center py-8 text-base-content/60">
            <div class="text-4xl mb-2">🧐</div>
            <p>没有找到符合条件的任务</p>
          </div>

          <div v-else class="flex flex-col flex-1 overflow-hidden">
            <div class="flex-1 overflow-y-auto pr-2 space-y-4">
              <!-- New Task Card Layout -->
              <div
                v-for="task in filteredTasks"
                :key="task.task_id"
                class="bg-base-100/50 rounded-2xl shadow-md transition-all hover:shadow-lg hover:-translate-y-1"
              >
                <div class="p-4">
                  <!-- Card Header -->
                  <div class="flex justify-between items-start mb-3">
                    <div class="flex items-center gap-3">
                      <div class="text-2xl">📦</div>
                      <div>
                        <div class="font-bold text-base-content">
                          {{ task.dataset_identifier }}
                        </div>
                        <div class="text-xs text-base-content/70">
                          {{ task.model_name }}
                        </div>
                      </div>
                    </div>
                    <div
                      class="badge"
                      :class="{
                        'badge-info': task.status === 'running',
                        'badge-success': task.status === 'completed',
                        'badge-error': task.status === 'failed',
                        'badge-ghost': task.status === 'pending',
                      }"
                    >
                      {{ getStatusText(task.status) }}
                    </div>
                  </div>

                  <!-- Card Body: Progress and Parameters -->
                  <div class="mb-3">
                    <div
                      v-if="task.status === 'running' || task.status === 'completed'"
                      class="mb-3"
                    >
                      <div
                        class="flex items-center justify-between text-xs mb-1 text-base-content/80"
                      >
                        <span>Epoch {{ task.current_epoch }} / {{ task.total_epochs }}</span>
                        <span>{{ task.progress }}%</span>
                      </div>
                      <progress
                        class="progress w-full"
                        :class="{
                          'progress-info': task.status === 'running',
                          'progress-success': task.status === 'completed',
                        }"
                        :value="task.progress"
                        max="100"
                      ></progress>
                    </div>

                    <div class="flex items-center justify-between text-xs text-base-content/70">
                      <span
                        >Batch Size: <strong>{{ task.batch_size }}</strong></span
                      >
                      <span
                        >Image Size: <strong>{{ task.image_size }}</strong></span
                      >
                    </div>
                  </div>

                  <!-- Error Message -->
                  <div
                    v-if="task.status === 'failed' && task.error"
                    class="text-xs text-error p-2 bg-error/10 rounded-md mb-3"
                  >
                    <strong>错误:</strong> {{ task.error }}
                  </div>

                  <!-- Card Footer: Actions and Timestamp -->
                  <div class="flex justify-between items-center">
                    <div class="flex gap-2">
                      <button
                        v-if="task.logs && task.logs.length > 0"
                        class="btn btn-xs btn-outline"
                        @click="openLogModal(task)"
                      >
                        📋 查看日志
                      </button>
                      <button
                        v-if="task.status === 'running'"
                        @click="cancelTask(task.task_id)"
                        class="btn btn-xs btn-error"
                      >
                        ❌ 取消
                      </button>
                      <button
                        v-if="task.status === 'completed'"
                        @click="openResultsModal(task)"
                        class="btn btn-xs btn-success"
                      >
                        🏆 查看结果
                      </button>
                      <button
                        v-if="['completed', 'failed', 'cancelled'].includes(task.status)"
                        @click="confirmDelete(task.task_id)"
                        class="btn btn-xs btn-ghost"
                      >
                        🗑️ 删除
                      </button>
                    </div>
                    <div class="text-xs opacity-60">
                      {{ formatTime(task.created_at) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 日志查看弹窗 -->
    <div v-if="selectedTaskForLogs" class="modal modal-open" role="dialog">
      <div class="modal-box w-11/12 max-w-5xl">
        <div class="flex justify-between items-center mb-4">
          <h3 class="font-bold text-lg">
            📋 训练日志 - {{ selectedTaskForLogs.dataset_identifier }} ({{
              selectedTaskForLogs.task_id
            }})
          </h3>
          <button @click="closeLogModal" class="btn btn-sm btn-circle btn-ghost">✕</button>
        </div>

        <div class="bg-base-200 p-4 rounded-lg h-96 overflow-y-auto border border-base-300">
          <div v-if="selectedTaskForLogs.logs && selectedTaskForLogs.logs.length > 0">
            <!-- 训练参数折叠区域 -->
            <div class="mb-4">
              <div class="collapse collapse-arrow bg-base-100 rounded-lg">
                <input type="checkbox" v-model="showTrainingParams" />
                <div class="collapse-title text-sm font-medium flex items-center gap-2">
                  <span>📊 训练参数详情</span>
                  <span class="badge badge-sm badge-outline">
                    {{ getTrainingParamsCount(selectedTaskForLogs.logs) }} 个Epoch
                  </span>
                </div>
                <div class="collapse-content">
                  <div v-for="(item, index) in parseTrainingLogs(selectedTaskForLogs.logs)" :key="index" class="mb-3">
                    <!-- 只显示训练参数相关的内容 -->
                    <!-- Epoch 进度表头 -->
                    <div v-if="item.type === 'epoch_progress_header'" class="text-xs font-mono text-base-content/70 py-1 border-b border-base-300">
                      {{ item.text }}
                    </div>
                    
                    <!-- Epoch 训练进度 -->
                    <div v-else-if="item.type === 'epoch_progress'" class="bg-base-100 p-2 rounded-lg text-xs font-mono mb-2">
                      <div class="grid grid-cols-6 gap-1">
                        <div><span class="text-base-content/60">Epoch:</span> <span class="font-semibold">{{ item.epoch }}/{{ item.total_epochs }}</span></div>
                        <div><span class="text-base-content/60">GPU:</span> <span class="font-semibold">{{ item.gpu_mem }}</span></div>
                        <div><span class="text-base-content/60">Box:</span> <span class="font-semibold">{{ item.box_loss }}</span></div>
                        <div><span class="text-base-content/60">Cls:</span> <span class="font-semibold">{{ item.cls_loss }}</span></div>
                        <div><span class="text-base-content/60">DFL:</span> <span class="font-semibold">{{ item.dfl_loss }}</span></div>
                        <div><span class="text-base-content/60">进度:</span> <span class="font-semibold">{{ item.progress }}%</span></div>
                      </div>
                    </div>
                    
                    <!-- 验证表头 -->
                    <div v-else-if="item.type === 'validation_header'" class="text-xs font-mono text-base-content/70 py-1 border-b border-base-300">
                      {{ item.text }}
                    </div>
                    
                    <!-- 验证结果 -->
                    <div v-else-if="item.type === 'validation_result'" class="bg-success/5 p-2 rounded-lg text-xs font-mono mb-2">
                      <div class="grid grid-cols-7 gap-1">
                        <div><span class="text-base-content/60">Class:</span> <span class="font-semibold">{{ item.class_name }}</span></div>
                        <div><span class="text-base-content/60">Images:</span> <span class="font-semibold">{{ item.images }}</span></div>
                        <div><span class="text-base-content/60">Inst:</span> <span class="font-semibold">{{ item.instances }}</span></div>
                        <div><span class="text-base-content/60">Box(P):</span> <span class="font-semibold">{{ item.box_p }}</span></div>
                        <div><span class="text-base-content/60">R:</span> <span class="font-semibold">{{ item.recall }}</span></div>
                        <div><span class="text-base-content/60">mAP50:</span> <span class="font-semibold">{{ item.map50 }}</span></div>
                        <div><span class="text-base-content/60">mAP95:</span> <span class="font-semibold">{{ item.map50_95 }}</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 其他日志内容 -->
            <div v-for="(item, index) in getFilteredOtherLogs(selectedTaskForLogs.logs)" :key="'other-' + index" class="mb-3">
              <!-- Epoch 训练指标 -->
              <div v-if="item.type === 'epoch_metrics'" class="bg-base-100 p-3 rounded-lg">
                <div class="flex items-center gap-2 mb-2">
                  <span class="badge badge-info badge-sm">Epoch {{ item.epoch }}/{{ item.total }}</span>
                </div>
                <div class="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <span class="text-base-content/60">Box Loss:</span>
                    <span class="font-semibold ml-1">{{ item.box_loss }}</span>
                  </div>
                  <div>
                    <span class="text-base-content/60">Cls Loss:</span>
                    <span class="font-semibold ml-1">{{ item.cls_loss }}</span>
                  </div>
                  <div>
                    <span class="text-base-content/60">DFL Loss:</span>
                    <span class="font-semibold ml-1">{{ item.dfl_loss }}</span>
                  </div>
                </div>
              </div>
              
              <!-- 验证结果 -->
              <div v-else-if="item.type === 'validation_metrics'" class="bg-success/10 p-3 rounded-lg">
                <div class="flex items-center gap-2 mb-2">
                  <span class="badge badge-success badge-sm">验证 - Epoch {{ item.epoch || '?' }}</span>
                  <span class="text-xs text-base-content/70">{{ item.target }} ({{ item.images }} 张)</span>
                </div>
                <div class="grid grid-cols-4 gap-2 text-xs">
                  <div>
                    <span class="text-base-content/60">精确度:</span>
                    <span class="font-semibold ml-1">{{ (parseFloat(item.precision) * 100).toFixed(2) }}%</span>
                  </div>
                  <div>
                    <span class="text-base-content/60">召回率:</span>
                    <span class="font-semibold ml-1">{{ (parseFloat(item.recall) * 100).toFixed(2) }}%</span>
                  </div>
                  <div>
                    <span class="text-base-content/60">mAP50:</span>
                    <span class="font-semibold ml-1">{{ (parseFloat(item.map50) * 100).toFixed(2) }}%</span>
                  </div>
                  <div>
                    <span class="text-base-content/60">mAP50-95:</span>
                    <span class="font-semibold ml-1">{{ (parseFloat(item.map50_95) * 100).toFixed(2) }}%</span>
                  </div>
                </div>
              </div>
      
              
              <!-- 类别详细结果 -->
              <div v-else-if="item.type === 'class_result'" class="bg-primary/10 p-3 rounded-lg">
                <div class="flex items-center gap-2 mb-2">
                  <span class="badge badge-primary badge-sm">{{ item.class_name }}</span>
                  <span class="text-xs text-base-content/70">{{ item.images }} 张图片, {{ item.instances }} 个实例</span>
                </div>
                <div class="grid grid-cols-4 gap-2 text-xs">
                  <div>
                    <span class="text-base-content/60">Precision:</span>
                    <span class="font-semibold ml-1">{{ item.precision }}</span>
                  </div>
                  <div>
                    <span class="text-base-content/60">Recall:</span>
                    <span class="font-semibold ml-1">{{ item.recall }}</span>
                  </div>
                  <div>
                    <span class="text-base-content/60">mAP50:</span>
                    <span class="font-semibold ml-1">{{ item.map50 }}</span>
                  </div>
                  <div>
                    <span class="text-base-content/60">mAP50-95:</span>
                    <span class="font-semibold ml-1">{{ item.map50_95 }}</span>
                  </div>
                </div>
              </div>
              
              <!-- 模型摘要 -->
              <div v-else-if="item.type === 'model_summary'" class="bg-info/10 p-3 rounded-lg">
                <div class="flex items-center gap-2">
                  <span class="badge badge-info badge-sm">{{ item.model }}</span>
                  <span class="text-xs text-base-content/70">{{ item.layers }} 层, {{ item.parameters }} 参数</span>
                </div>
              </div>
              
              <!-- 训练完成 -->
              <div v-else-if="item.type === 'training_complete'" class="bg-success/10 p-3 rounded-lg text-sm text-success-content">
                ✅ {{ item.text }}
              </div>
              
              <!-- 权重保存 -->
              <div v-else-if="item.type === 'weight_saved'" class="text-xs text-base-content/70 py-1">
                💾 权重已保存: {{ item.path }}
              </div>
              
              <!-- 验证权重 -->
              <div v-else-if="item.type === 'validating'" class="text-xs text-base-content/70 py-1">
                🔍 正在验证: {{ item.path }}
              </div>
              
              <!-- 结果保存 -->
              <div v-else-if="item.type === 'results_saved'" class="text-xs text-base-content/70 py-1">
                📁 {{ item.text }}
              </div>
              
              <!-- 其他重要信息 -->
              <div v-else-if="item.type === 'info'" class="bg-base-100 p-3 rounded-lg text-sm text-base-content/80">
                <span v-if="item.text.includes('Transferred')" class="text-info">📦</span>
                <span v-else-if="item.text.includes('Image sizes')" class="text-primary">🖼️</span>
                <span v-else-if="item.text.includes('Starting training')" class="text-success">🚀</span>
                {{ item.text }}
              </div>
              
              <!-- Training completed successfully -->
              <div v-else-if="item.type === 'training_success'" class="bg-success/10 p-3 rounded-lg text-sm">
                ✅ <span class="font-semibold text-success-content">{{ item.text }}</span>
              </div>
            </div>
          </div>
          <div v-else class="text-center text-base-content/60 pt-8">暂无日志信息</div>
        </div>

        <div class="modal-action">
          <button @click="closeLogModal" class="btn">关闭</button>
        </div>
      </div>
    </div>

    <!-- 训练结果查看弹窗 -->
    <div v-if="selectedTaskForResults" class="modal modal-open" role="dialog">
      <div class="modal-box w-11/12 max-w-7xl h-[95vh] flex flex-col p-3">
        <div class="flex justify-between items-center mb-3">
          <h3 class="font-bold text-base">
            🏆 训练结果 - {{ selectedTaskForResults.dataset_identifier }}
          </h3>
          <button @click="closeResultsModal" class="btn btn-sm btn-circle btn-ghost">✕</button>
        </div>

        <div v-if="loadingResults" class="flex justify-center items-center py-8">
          <span class="loading loading-spinner loading-lg"></span>
        </div>

        <div v-else class="space-y-2 flex-1 flex flex-col">
          <!-- 基本信息和训练模型 -->
          <div class="flex gap-4 flex-shrink-0">
            <!-- 左侧：基本信息 -->
            <div class="grid grid-cols-4 gap-2 flex-1">
              <div class="stat bg-base-200 rounded-lg p-2">
                <div class="stat-title text-xs">训练轮数</div>
                <div class="stat-value text-lg">{{ selectedTaskForResults.epochs }}</div>
              </div>
              <div class="stat bg-base-200 rounded-lg p-2">
                <div class="stat-title text-xs">批次大小</div>
                <div class="stat-value text-lg">{{ selectedTaskForResults.batch_size }}</div>
              </div>
              <div class="stat bg-base-200 rounded-lg p-2">
                <div class="stat-title text-xs">图片尺寸</div>
                <div class="stat-value text-lg">{{ selectedTaskForResults.image_size }}</div>
              </div>
              <div class="stat bg-base-200 rounded-lg p-2">
                <div class="stat-title text-xs">训练时长</div>
                <div class="stat-value text-lg">
                  {{ formatDuration(selectedTaskForResults.duration_seconds) }}
                </div>
              </div>
            </div>

            <!-- 右侧：训练模型 -->
            <div
              v-if="
                selectedTaskForResults.model_files && selectedTaskForResults.model_files.length > 0
              "
              class="flex flex-col justify-center gap-1"
            >
              <div
                v-for="file in selectedTaskForResults.model_files"
                :key="file"
                class="badge badge-md bg-base-200 whitespace-nowrap"
              >
                📦 {{ file }}
              </div>
            </div>
          </div>

          <!-- Epoch指标表格 -->
          <div
            v-if="
              selectedTaskForResults.epoch_metrics &&
              selectedTaskForResults.epoch_metrics.length > 0
            "
            class="flex-shrink-0"
          >
            <h4 class="font-bold mb-1 text-sm">📈 训练指标</h4>
            <div class="overflow-x-auto max-h-32 overflow-y-auto">
              <table class="table table-xs table-zebra">
                <thead>
                  <tr>
                    <th>Epoch</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>mAP50</th>
                    <th>mAP75</th>
                    <th>Box Loss</th>
                    <th>Cls Loss</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="metric in selectedTaskForResults.epoch_metrics" :key="metric.epoch">
                    <td>{{ metric.epoch }}</td>
                    <td>{{ metric.precision?.toFixed(4) || '-' }}</td>
                    <td>{{ metric.recall?.toFixed(4) || '-' }}</td>
                    <td>{{ metric.map50?.toFixed(4) || '-' }}</td>
                    <td>{{ metric.map75?.toFixed(4) || '-' }}</td>
                    <td>{{ metric.box_loss?.toFixed(4) || '-' }}</td>
                    <td>{{ metric.cls_loss?.toFixed(4) || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 结果图片轮播 -->
          <div
            v-if="
              selectedTaskForResults.result_images &&
              selectedTaskForResults.result_images.length > 0
            "
            class="flex-1 flex flex-col min-h-0"
          >
            <h4 class="font-bold mb-1 text-sm flex-shrink-0">📊 训练图表</h4>
            <div class="carousel w-full rounded-lg bg-base-200 flex-1">
              <div
                v-for="(image, index) in selectedTaskForResults.result_images"
                :key="image"
                :id="`slide${index}`"
                class="carousel-item relative w-full"
              >
                <div class="w-full p-4">
                  <div class="text-center mb-2">
                    <p class="text-sm font-semibold">{{ image }}</p>
                  </div>
                  <div class="flex justify-center items-center rounded-lg">
                    <img
                      :src="`/train/runs/detect/${selectedTaskForResults.task_id}/${image}`"
                      :alt="image"
                      class="max-w-full max-h-[500px] object-contain rounded-lg"
                      @error="
                        (e) => {
                          e.target.style.display = 'none'
                          e.target.nextElementSibling.style.display = 'flex'
                        }
                      "
                    />
                    <div
                      class="hidden flex-col justify-center items-center bg-base-300 rounded-lg p-8"
                      style="min-height: 400px"
                    >
                      <p class="text-sm text-base-content/50 mb-2">图片加载失败</p>
                      <p class="text-xs text-base-content/40">{{ image }}</p>
                    </div>
                  </div>
                </div>
                <div
                  class="absolute flex justify-between transform -translate-y-1/2 left-5 right-5 top-1/2"
                >
                  <a
                    :href="`#slide${index === 0 ? selectedTaskForResults.result_images.length - 1 : index - 1}`"
                    class="btn btn-circle btn-sm"
                  >
                    ❮
                  </a>
                  <a
                    :href="`#slide${index === selectedTaskForResults.result_images.length - 1 ? 0 : index + 1}`"
                    class="btn btn-circle btn-sm"
                  >
                    ❯
                  </a>
                </div>
              </div>
            </div>

            <!-- 指示器 -->
            <div class="flex justify-center w-full py-2 gap-2">
              <a
                v-for="(image, index) in selectedTaskForResults.result_images"
                :key="`indicator-${index}`"
                :href="`#slide${index}`"
                class="btn btn-xs"
              >
                {{ index + 1 }}
              </a>
            </div>
          </div>
        </div>

        <div class="modal-action flex-shrink-0 mt-3 pt-3 border-t border-base-200">
          <button @click="closeResultsModal" class="btn btn-sm">关闭</button>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

interface Dataset {
  identifier: string
  name: string
  yaml_path: string
  train_images: number
  val_images: number
  total_images: number
}

interface ModelInfo {
  name: string
  is_local: boolean
  is_downloadable: boolean
  size?: string
}

interface TrainingTask {
  task_id: string
  dataset_identifier: string
  model_name: string
  epochs: number
  batch_size: number
  image_size: number
  status: string
  progress: number
  current_epoch: number
  total_epochs: number
  created_at: string
  started_at?: string
  completed_at?: string
  error?: string
  results_dir?: string
  logs?: string[]
  showLogs?: boolean // For UI state
}

const datasets = ref<Dataset[]>([])
const models = ref<ModelInfo[]>([])
const tasks = ref<TrainingTask[]>([])
const message = ref('')
const messageType = ref('alert-info')
const creating = ref(false)
const selectedTaskForLogs = ref<TrainingTask | null>(null)
const filterStatus = ref('all') // 'all', 'running', 'completed', 'failed'
const downloading = ref(false)
const downloadProgress = ref<{
  progress: number
  downloaded: number
  total: number
  status: string
} | null>(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const fileInput = ref<HTMLInputElement | null>(null)
const showTrainingParams = ref(false) // 控制训练参数折叠展开

const trainingForm = ref({
  dataset: '',
  model: '',
  epochs: 100,
  batchSize: 16,
  imageSize: 640,
})

const selectedDataset = computed(() => {
  return datasets.value.find((d) => d.identifier === trainingForm.value.dataset)
})

const selectedModel = computed(() => {
  return models.value.find((m) => m.name === trainingForm.value.model)
})

const canStartTraining = computed(() => {
  const hasDataset = !!trainingForm.value.dataset
  const hasModel = !!trainingForm.value.model
  const modelIsLocal = selectedModel.value?.is_local
  return hasDataset && hasModel && modelIsLocal
})

const sortedTasks = computed(() => {
  return [...tasks.value].sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })
})

const filteredTasks = computed(() => {
  if (filterStatus.value === 'all') {
    return sortedTasks.value
  }
  return sortedTasks.value.filter((task) => task.status === filterStatus.value)
})

let statusInterval: number | null = null

const loadResources = async () => {
  try {
    // 加载数据集列表
    const datasetsRes = await axios.get('/api/train/datasets')
    datasets.value = datasetsRes.data.datasets || []

    // 加载模型列表
    const modelsRes = await axios.get('/api/train/models')
    models.value = modelsRes.data.models || []

    // 加载训练任务列表
    await loadTasks()
  } catch (error) {
    console.error('加载资源失败:', error)
    showMessage('加载资源失败', 'alert-error')
  }
}

const loadTasks = async () => {
  try {
    const response = await axios.get('/api/train/tasks')
    const newTasks = response.data.tasks || []

    // Preserve the showLogs state for existing tasks
    const updatedTasks = newTasks.map((newTask: TrainingTask) => {
      const existingTask = tasks.value.find((t) => t.task_id === newTask.task_id)
      return {
        ...newTask,
        showLogs: existingTask ? existingTask.showLogs : false,
      }
    })

    tasks.value = updatedTasks
  } catch (error) {
    console.error('加载任务列表失败:', error)
  }
}

const startTraining = async () => {
  if (!canStartTraining.value) {
    showMessage('请选择数据集和模型', 'alert-warning')
    return
  }

  creating.value = true
  try {
    // 创建训练任务
    const createRes = await axios.post('/api/train/create', {
      dataset_identifier: trainingForm.value.dataset,
      model_name: trainingForm.value.model,
      epochs: trainingForm.value.epochs,
      batch_size: trainingForm.value.batchSize,
      image_size: trainingForm.value.imageSize,
    })

    const task = createRes.data

    // 启动训练
    await axios.post(`/api/train/${task.task_id}/start`)

    showMessage('训练已开始', 'alert-success')

    // 重置表单
    trainingForm.value.dataset = ''
    trainingForm.value.model = ''

    // 重新加载任务列表并启动轮询
    await loadTasks()
    ensurePolling() // 确保启动轮询
  } catch (error: any) {
    console.error('启动训练失败:', error)
    showMessage(error.response?.data?.detail || error.message || '启动训练失败', 'alert-error')
  } finally {
    creating.value = false
  }
}


const cancelTask = async (taskId: string) => {
  try {
    await axios.post(`/api/train/${taskId}/cancel`)
    showMessage('训练已取消', 'alert-success')
    await loadTasks()
  } catch (error: any) {
    console.error('取消训练失败:', error)
    showMessage(error.response?.data?.detail || error.message || '取消训练失败', 'alert-error')
  }
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    pending: '等待中',
    running: '训练中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return statusMap[status] || status
}

const formatTime = (timeStr: string) => {
  try {
    const date = new Date(timeStr)
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return timeStr
  }
}

const downloadModel = async (modelName: string) => {
  downloading.value = true
  downloadProgress.value = null

  try {
    showMessage(`正在下载模型 ${modelName}...`, 'alert-info')

    // 启动下载
    const downloadPromise = axios.post(`/api/train/models/${modelName}/download`)

    // 启动进度轮询
    const progressInterval = setInterval(async () => {
      try {
        const progressRes = await axios.get(`/api/train/models/${modelName}/download-progress`)
        downloadProgress.value = progressRes.data

        // 如果下载完成或失败，停止轮询
        if (progressRes.data.status === 'completed' || progressRes.data.status === 'failed') {
          clearInterval(progressInterval)
        }
      } catch (error) {
        console.error('获取下载进度失败:', error)
      }
    }, 500) // 每500ms更新一次进度

    // 等待下载完成
    const response = await downloadPromise
    clearInterval(progressInterval)

    showMessage(response.data.message || '模型下载成功', 'alert-success')

    // 重新加载模型列表
    await loadResources()
  } catch (error: any) {
    console.error('下载模型失败:', error)
    showMessage(error.response?.data?.detail || error.message || '下载模型失败', 'alert-error')
  } finally {
    downloading.value = false
    downloadProgress.value = null
  }
}

const triggerFileUpload = () => {
  fileInput.value?.click()
}

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file) return

  // 验证文件扩展名
  if (!file.name.endsWith('.pt')) {
    showMessage('只能上传 .pt 格式的模型文件', 'alert-error')
    return
  }

  uploading.value = true
  uploadProgress.value = 0

  try {
    const formData = new FormData()
    formData.append('file', file)

    // 使用 XMLHttpRequest 以便监听上传进度
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()

      // 上传进度
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          uploadProgress.value = (e.loaded / e.total) * 100
        }
      })

      // 上传完成
      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.response)
        } else {
          reject(new Error(xhr.statusText))
        }
      })

      // 上传错误
      xhr.addEventListener('error', () => {
        reject(new Error('上传失败'))
      })

      xhr.open('POST', '/api/train/models/upload')
      xhr.send(formData)
    })

    showMessage('模型上传成功', 'alert-success')

    // 重新加载模型列表
    await loadResources()
  } catch (error: any) {
    console.error('上传模型失败:', error)
    showMessage(error.message || '上传模型失败', 'alert-error')
  } finally {
    uploading.value = false
    uploadProgress.value = 0
    // 清除文件选择
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const openLogModal = (task: TrainingTask) => {
  selectedTaskForLogs.value = task
}

const closeLogModal = () => {
  selectedTaskForLogs.value = null
}

const showMessage = (msg: string, type: string = 'alert-info') => {
  message.value = msg
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 3000)
}

// 定时更新训练状态
const startStatusPolling = () => {
  statusInterval = window.setInterval(async () => {
    await loadTasks()
    
    // 如果没有正在运行的任务，停止轮询
    const hasRunningTasks = tasks.value.some(task => task.status === 'running')
    if (!hasRunningTasks) {
      stopStatusPolling()
    }
  }, 2000) // 每2秒更新一次
}

const stopStatusPolling = () => {
  if (statusInterval) {
    clearInterval(statusInterval)
    statusInterval = null
  }
}

// 当有任务开始时，重新启动轮询
const ensurePolling = () => {
  if (!statusInterval) {
    startStatusPolling()
  }
}


const confirmDelete = async (taskId: string) => {
  if (!confirm('确定要删除这条训练记录吗？\n注意：这将删除所有训练结果和模型文件。')) {
    return
  }

  try {
    await axios.delete(`/api/train/${taskId}`)
    showMessage('训练记录已删除', 'alert-success')
    await loadTasks()
  } catch (error: any) {
    console.error('删除训练记录失败:', error)
    showMessage(error.response?.data?.detail || error.message || '删除训练记录失败', 'alert-error')
  }
}

const selectedTaskForResults = ref<any>(null)
const loadingResults = ref(false)

const openResultsModal = async (task: TrainingTask) => {
  loadingResults.value = true
  try {
    const response = await axios.get(`/api/train/${task.task_id}/results`)
    selectedTaskForResults.value = response.data
  } catch (error: any) {
    console.error('获取训练结果失败:', error)
    showMessage(error.response?.data?.detail || error.message || '获取训练结果失败', 'alert-error')
  } finally {
    loadingResults.value = false
  }
}

const closeResultsModal = () => {
  selectedTaskForResults.value = null
}

const formatDuration = (seconds: number | null) => {
  if (!seconds) return '-'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟${secs}秒`
  } else {
    return `${secs}秒`
  }
}

const handleImageError = (e: Event) => {
  const target = e.target as HTMLImageElement
  if (target && target.nextElementSibling) {
    target.style.display = 'none'
    const errorDiv = target.nextElementSibling as HTMLElement
    errorDiv.style.display = 'flex'
  }
}

// 过滤掉训练参数相关的内容，只显示其他重要信息
const getFilteredOtherLogs = (logs: string[]) => {
  const parsedLogs = parseTrainingLogs(logs)
  return parsedLogs.filter(item => 
    item.type !== 'epoch_progress_header' && 
    item.type !== 'epoch_progress' && 
    item.type !== 'validation_header' && 
    item.type !== 'validation_result'
  )
}

// 解析训练日志，提取关键信息
const parseTrainingLogs = (logs: string[]) => {
  const parsedLogs: any[] = []
  
  for (const log of logs) {
    // 清理 ANSI 转义序列
    // eslint-disable-next-line no-control-regex
    let cleaned = log.replace(/\x1B\[[0-9;]*[a-zA-Z]/g, '').replace(/\[K/g, '').trim()
    
    // 跳过不需要显示的内容
    if (!cleaned || 
        cleaned.includes('ultralytics.nn.modules') ||
        cleaned.includes('torch.nn.modules') ||
        cleaned.includes('optimizer:') ||
        cleaned.includes('Freezing layer') ||
        cleaned.includes('Using 0 dataloader') ||
        cleaned.includes('Closing dataloader') ||
        cleaned.includes('Fast image access') ||
        cleaned.includes('New cache created') ||
        cleaned.includes('Plotting labels') ||
        cleaned.includes('Logging results')) {
      continue
    }
    
    // 解析 Epoch 表头（Epoch    GPU_mem   box_loss   cls_loss   dfl_loss  Instances       Size）
    if (cleaned.includes('Epoch') && cleaned.includes('GPU_mem') && cleaned.includes('box_loss')) {
      parsedLogs.push({
        type: 'epoch_progress_header',
        text: cleaned
      })
      continue
    }
    
    // 解析训练进度行（包含进度条的行）
    // 示例: "1/10         0G      1.115      4.194      1.437         17        640: 0% ──────────── 0/6  13.5s"
    const progressMatch = cleaned.match(/(\d+)\/(\d+)\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+):\s*(\d+)%/)
    if (progressMatch) {
      parsedLogs.push({
        type: 'epoch_progress',
        epoch: progressMatch[1],
        total_epochs: progressMatch[2],
        gpu_mem: progressMatch[3],
        box_loss: progressMatch[4],
        cls_loss: progressMatch[5],
        dfl_loss: progressMatch[6],
        instances: progressMatch[7],
        size: progressMatch[8],
        progress: progressMatch[9],
        raw: cleaned
      })
      continue
    }
    
    // 解析验证表头（Class     Images  Instances      Box(P          R      mAP50  mAP50-95)）
    if (cleaned.includes('Class') && cleaned.includes('Images') && cleaned.includes('Instances') && cleaned.includes('Box(P')) {
      parsedLogs.push({
        type: 'validation_header',
        text: cleaned
      })
      continue
    }
    
    // 解析验证结果行（all         24         27    0.00542      0.938       0.31      0.229）
    const valResultMatch = cleaned.match(/^(all|[\u4e00-\u9fa5\w]+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)$/)
    if (valResultMatch) {
      parsedLogs.push({
        type: 'validation_result',
        class_name: valResultMatch[1],
        images: valResultMatch[2],
        instances: valResultMatch[3],
        box_p: valResultMatch[4],
        recall: valResultMatch[5],
        map50: valResultMatch[6],
        map50_95: valResultMatch[7]
      })
      continue
    }
    
    // 解析 Epoch 标题行
    if (cleaned.match(/^Epoch\s+\d+\/\d+$/)) {
      const epochMatch = cleaned.match(/Epoch\s+(\d+)\/(\d+)/)
      if (epochMatch) {
        parsedLogs.push({
          type: 'epoch_header',
          epoch: epochMatch[1],
          total: epochMatch[2]
        })
      }
      continue
    }
    
    // 解析训练指标（Box Loss, Cls Loss, DFL Loss）
    if (cleaned.startsWith('Box Loss:') || cleaned.startsWith('Cls Loss:') || cleaned.startsWith('DFL Loss:')) {
      const lossMatch = cleaned.match(/(Box Loss|Cls Loss|DFL Loss):([\d.]+)/)
      if (lossMatch) {
        // 查找最近的 epoch_header
        const lastEpoch = [...parsedLogs].reverse().find(item => item.type === 'epoch_header')
        if (lastEpoch) {
          // 如果这个 epoch 还没有 metrics，创建一个
          let metrics = parsedLogs.find(item => item.type === 'epoch_metrics' && item.epoch === lastEpoch.epoch)
          if (!metrics) {
            metrics = {
              type: 'epoch_metrics',
              epoch: lastEpoch.epoch,
              total: lastEpoch.total,
              box_loss: '-',
              cls_loss: '-',
              dfl_loss: '-'
            }
            parsedLogs.push(metrics)
          }
          
          if (lossMatch[1] === 'Box Loss') metrics.box_loss = lossMatch[2]
          else if (lossMatch[1] === 'Cls Loss') metrics.cls_loss = lossMatch[2]
          else if (lossMatch[1] === 'DFL Loss') metrics.dfl_loss = lossMatch[2]
        }
      }
      continue
    }
    
    // 解析验证结果标题
    if (cleaned === '验证结果') {
      parsedLogs.push({
        type: 'validation_header'
      })
      continue
    }
    
    // 解析具体的类别验证结果或总体结果
    const valMatch = cleaned.match(/^(\S+)\s+-\s+(\d+)\s+张\s+张图片$/)
    if (valMatch) {
      // 这是 "all - 24 张 张图片" 格式
      parsedLogs.push({
        type: 'validation_target',
        target: valMatch[1],
        images: valMatch[2]
      })
      continue
    }
    
    // 解析指标值（Precision, Recall, mAP50, mAP50-95）
    if (cleaned.startsWith('Precision:') || cleaned.startsWith('Recall:') || 
        cleaned.startsWith('mAP50:') || cleaned.startsWith('mAP50-95:')) {
      const metricMatch = cleaned.match(/(Precision|Recall|mAP50|mAP50-95):([\d.]+)/)
      if (metricMatch) {
        const lastTarget = [...parsedLogs].reverse().find(item => item.type === 'validation_target')
        if (lastTarget) {
          // 找到最近的 epoch_metrics 来确定当前 epoch
          const lastEpoch = [...parsedLogs].reverse().find(item => item.type === 'epoch_metrics')
          
          let valMetrics = parsedLogs.find(item => 
            item.type === 'validation_metrics' && 
            item.target === lastTarget.target && 
            item.epoch === (lastEpoch ? lastEpoch.epoch : null)
          )
          if (!valMetrics) {
            valMetrics = {
              type: 'validation_metrics',
              target: lastTarget.target,
              images: lastTarget.images,
              epoch: lastEpoch ? lastEpoch.epoch : null,
              precision: '-',
              recall: '-',
              map50: '-',
              map50_95: '-'
            }
            parsedLogs.push(valMetrics)
          }
          
          if (metricMatch[1] === 'Precision') valMetrics.precision = metricMatch[2]
          else if (metricMatch[1] === 'Recall') valMetrics.recall = metricMatch[2]
          else if (metricMatch[1] === 'mAP50') valMetrics.map50 = metricMatch[2]
          else if (metricMatch[1] === 'mAP50-95') valMetrics.map50_95 = metricMatch[2]
        }
      }
      continue
    }
      
    
    // 解析每个类别的最终结果（如：小橘 8 8 0.00305 1 0.755 0.628）
    const classMatch = cleaned.match(/^(\S+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)$/)
    if (classMatch && !cleaned.startsWith('all')) {
      parsedLogs.push({
        type: 'class_result',
        class_name: classMatch[1],
        images: classMatch[2],
        instances: classMatch[3],
        precision: classMatch[4],
        recall: classMatch[5],
        map50: classMatch[6],
        map50_95: classMatch[7]
      })
      continue
    }
    
    // 模型摘要
    if (cleaned.includes('summary') && cleaned.includes('layers') && cleaned.includes('parameters')) {
      const summaryMatch = cleaned.match(/(\S+)\s+summary.*?(\d+)\s+layers,\s+([\d,]+)\s+parameters/)
      if (summaryMatch) {
        parsedLogs.push({
          type: 'model_summary',
          model: summaryMatch[1],
          layers: summaryMatch[2],
          parameters: summaryMatch[3]
        })
      }
      continue
    }
    
    // 训练完成信息
    if (cleaned.includes('epochs completed in') || cleaned.includes('hours')) {
      parsedLogs.push({
        type: 'training_complete',
        text: cleaned
      })
      continue
    }
    
    // 权重保存信息
    if (cleaned.includes('Optimizer stripped from') && cleaned.includes('.pt')) {
      const weightMatch = cleaned.match(/from\s+(.*?\.pt)/)
      if (weightMatch) {
        parsedLogs.push({
          type: 'weight_saved',
          path: weightMatch[1]
        })
      }
      continue
    }
    
    // 验证权重信息
    if (cleaned.startsWith('Validating') && cleaned.includes('.pt')) {
      const validateMatch = cleaned.match(/Validating\s+(.*?\.pt)/)
      if (validateMatch) {
        parsedLogs.push({
          type: 'validating',
          path: validateMatch[1]
        })
      }
      continue
    }
    
    // Results saved to
    if (cleaned.startsWith('Results saved to')) {
      parsedLogs.push({
        type: 'results_saved',
        text: cleaned
      })
      continue
    }
    
    // Training completed successfully
    if (cleaned === 'Training completed successfully') {
      parsedLogs.push({
        type: 'training_success',
        text: cleaned
      })
      continue
    }
    
    // 其他重要信息
    if (cleaned.startsWith('Starting training') ||
        cleaned.startsWith('Transferred') ||
        cleaned.includes('Image sizes')) {
      parsedLogs.push({
        type: 'info',
        text: cleaned
      })
    }
      
  }
  
  // 过滤掉孤立的 header（没有对应数据的）
  return parsedLogs.filter((item, index) => {
    if (item.type === 'epoch_header') {
      return parsedLogs.some((other, otherIndex) => 
        otherIndex > index && other.type === 'epoch_metrics' && other.epoch === item.epoch
      )
    }
    if (item.type === 'validation_header') {
      return parsedLogs.some((other, otherIndex) => 
        otherIndex > index && (other.type === 'validation_target' || other.type === 'validation_metrics')
      )
    }
    if (item.type === 'validation_target') {
      return parsedLogs.some((other) => 
        other.type === 'validation_metrics' && other.target === item.target
      )
    }
    return true
  })
}

// 统计训练参数数量
const getTrainingParamsCount = (logs: string[]) => {
  const parsedLogs = parseTrainingLogs(logs)
  return parsedLogs.filter(item => item.type === 'epoch_progress').length
}

onMounted(async () => {
  await loadResources()
  
  // 只有在有运行中的任务时才启动轮询
  const hasRunningTasks = tasks.value.some(task => task.status === 'running')
  if (hasRunningTasks) {
    startStatusPolling()
  }
})


onUnmounted(() => {
  stopStatusPolling()
})
</script>

<style scoped lang="scss">
@use '@/styles/glassmorphism.scss';

.train-page {
  height: 100vh;
  background: linear-gradient(135deg, #fef3c7 0%, #d1fae5 100%);
  padding: 20px;
}

.glass-panel {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  overflow-y: auto;
}
</style>
