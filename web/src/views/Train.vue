<template>
  <div class="page-container">
    <div class="train-layout">
      <!-- 左侧内容区域 (20%) -->
      <div class="train-controls glass-panel">
        <h1 class="text-2xl font-bold mb-6">🤖 模型训练</h1>

        <div class="train-form">
          <div class="form-group">
            <label for="model-select" class="label">
              <span class="label-text font-semibold">选择模型</span>
            </label>
            <select id="model-select" v-model="selectedModel" class="select select-bordered w-full">
              <option value="">请选择模型</option>
              <option v-for="model in models" :key="model" :value="model">
                {{ model }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label for="dataset-select" class="label">
              <span class="label-text font-semibold">选择数据集</span>
            </label>
            <select
              id="dataset-select"
              v-model="selectedDataset"
              class="select select-bordered w-full"
            >
              <option value="">请选择数据集</option>
              <option v-for="dataset in datasets" :key="dataset" :value="dataset">
                {{ dataset }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label for="epochs" class="label">
              <span class="label-text font-semibold">训练轮数</span>
            </label>
            <input
              type="number"
              id="epochs"
              v-model.number="epochs"
              class="input input-bordered w-full"
              min="1"
              max="1000"
              placeholder="训练轮数"
            />
          </div>

          <div class="form-group">
            <label for="img-size" class="label">
              <span class="label-text font-semibold">图像尺寸</span>
            </label>
            <input
              type="number"
              id="img-size"
              v-model.number="imgSize"
              class="input input-bordered w-full"
              min="32"
              max="1280"
              placeholder="图像尺寸"
            />
          </div>

          <div class="form-group">
            <label for="batch-size" class="label">
              <span class="label-text font-semibold">批次大小</span>
            </label>
            <input
              type="number"
              id="batch-size"
              v-model.number="batchSize"
              class="input input-bordered w-full"
              min="1"
              max="64"
              placeholder="批次大小"
            />
          </div>

          <button
            @click="startTraining"
            :disabled="!canStartTraining || isTraining"
            class="btn btn-primary w-full mt-4"
          >
            {{ isTraining ? '训练中...' : '开始训练' }}
          </button>
        </div>

        <div v-if="trainingJobId" class="training-status mt-6">
          <h2 class="text-xl font-bold mb-4">📊 训练状态</h2>
          <div class="status-info space-y-2 bg-base-100 p-4 rounded-lg">
            <p><strong>任务ID:</strong> {{ trainingJobId }}</p>
            <p><strong>当前模型:</strong> {{ selectedModel }}</p>
            <p><strong>当前数据集:</strong> {{ selectedDataset }}</p>
          </div>

          <div class="logs-container mt-4">
            <h3 class="text-lg font-bold mb-2">📝 训练日志</h3>
            <div
              class="logs bg-gray-800 text-green-400 p-4 rounded-lg h-60 overflow-y-auto font-mono text-sm"
            >
              <div v-for="(log, index) in logs" :key="index" class="log-entry">
                {{ log }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧占位区域 (80%) -->
      <div class="visualization-area glass-panel">
        <h2 class="text-2xl font-bold mb-6">📈 训练可视化</h2>
        <div class="placeholder-content">
          <div class="stat-card">
            <div class="stat-content">
              <div class="stat-icon text-5xl">📉</div>
              <div class="stat-label">训练图表将在此显示</div>
              <div class="stat-value">-</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'

// 数据
const models = ref<string[]>([])
const datasets = ref<string[]>([])
const selectedModel = ref<string>('')
const selectedDataset = ref<string>('')
const epochs = ref<number>(100)
const imgSize = ref<number>(640)
const batchSize = ref<number>(16)
const isTraining = ref<boolean>(false)
const trainingJobId = ref<string>('')
const logs = ref<string[]>([])

// 计算属性
const canStartTraining = computed(() => {
  return selectedModel.value && selectedDataset.value
})

// 方法
const fetchModels = async () => {
  try {
    const response = await fetch('/api/train/models')
    const data = await response.json()
    models.value = data.models || []
  } catch (error) {
    console.error('获取模型列表失败:', error)
  }
}

const fetchDatasets = async () => {
  try {
    const response = await fetch('/api/train/datasets')
    const data = await response.json()
    datasets.value = data.datasets || []
  } catch (error) {
    console.error('获取数据集列表失败:', error)
  }
}

const startTraining = async () => {
  if (!canStartTraining.value) {
    alert('请选择模型和数据集')
    return
  }

  isTraining.value = true

  try {
    const response = await fetch('/api/train/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model_name: selectedModel.value,
        dataset_name: selectedDataset.value,
        epochs: epochs.value,
        imgsz: imgSize.value,
        batch_size: batchSize.value,
      }),
    })

    const result = await response.json()

    if (response.ok) {
      trainingJobId.value = result.job_id
      alert('训练已开始')

      // 开始获取训练日志
      await fetchTrainingLogs()
    } else {
      alert(`训练启动失败: ${result.detail || '未知错误'}`)
    }
  } catch (error) {
    console.error('启动训练失败:', error)
    alert(`训练启动失败: ${error}`)
  } finally {
    isTraining.value = false
  }
}

const fetchTrainingLogs = async () => {
  if (!trainingJobId.value) return

  try {
    const response = await fetch(`/api/train/logs/${trainingJobId.value}`)
    const data = await response.json()

    if (response.ok) {
      logs.value = data.logs || []

      // 如果训练还在进行中，继续获取日志
      if (
        !isTraining.value &&
        data.logs &&
        data.logs.some((log: string) => log.includes('Training completed'))
      ) {
        isTraining.value = false
      } else if (isTraining.value) {
        // 递归调用以持续获取日志
        setTimeout(fetchTrainingLogs, 2000)
      }
    }
  } catch (error) {
    console.error('获取训练日志失败:', error)
  }

  // 如果还在训练中，继续尝试获取日志
  if (isTraining.value) {
    setTimeout(fetchTrainingLogs, 2000)
  }
}

// 生命周期
onMounted(() => {
  fetchModels()
  fetchDatasets()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
  height: 100vh;
  background: linear-gradient(135deg, #a5b4fc 0%, #ddd6fe 50%, #fecaca 100%);
}

.train-layout {
  display: flex;
  gap: 20px;
  height: 100%;
}

.train-controls {
  flex: 0 0 20%;
  padding: 24px;
  border-radius: 1rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  max-height: 100%;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.visualization-area {
  flex: 0 0 80%;
  padding: 24px;
  border-radius: 1rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  max-height: 100%;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.placeholder-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.stat-card {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: white;
  border-radius: 16px;
  border: 2px solid rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.stat-icon {
  font-size: 40px;
  flex-shrink: 0;
}

.stat-label {
  font-size: 1rem;
  opacity: 0.7;
  font-weight: 500;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  line-height: 1;
}

@media (max-width: 768px) {
  .train-layout {
    flex-direction: column;
  }

  .train-controls,
  .visualization-area {
    flex: auto;
  }
}
</style>
