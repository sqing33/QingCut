<template>
  <div class="train-container">
    <h1>模型训练</h1>
    
    <div class="train-form">
      <div class="form-group">
        <label for="model-select">选择模型:</label>
        <select id="model-select" v-model="selectedModel" class="form-control">
          <option value="">请选择模型</option>
          <option v-for="model in models" :key="model" :value="model">
            {{ model }}
          </option>
        </select>
      </div>
      
      <div class="form-group">
        <label for="dataset-select">选择数据集:</label>
        <select id="dataset-select" v-model="selectedDataset" class="form-control">
          <option value="">请选择数据集</option>
          <option v-for="dataset in datasets" :key="dataset" :value="dataset">
            {{ dataset }}
          </option>
        </select>
      </div>
      
      <div class="form-group">
        <label for="epochs">训练轮数:</label>
        <input 
          type="number" 
          id="epochs" 
          v-model.number="epochs" 
          class="form-control" 
          min="1" 
          max="1000"
          placeholder="训练轮数"
        />
      </div>
      
      <div class="form-group">
        <label for="img-size">图像尺寸:</label>
        <input 
          type="number" 
          id="img-size" 
          v-model.number="imgSize" 
          class="form-control" 
          min="32" 
          max="1280"
          placeholder="图像尺寸"
        />
      </div>
      
      <div class="form-group">
        <label for="batch-size">批次大小:</label>
        <input 
          type="number" 
          id="batch-size" 
          v-model.number="batchSize" 
          class="form-control" 
          min="1" 
          max="64"
          placeholder="批次大小"
        />
      </div>
      
      <button 
        @click="startTraining" 
        :disabled="!canStartTraining || isTraining" 
        class="btn btn-primary"
      >
        {{ isTraining ? '训练中...' : '开始训练' }}
      </button>
    </div>
    
    <div v-if="trainingJobId" class="training-status">
      <h2>训练状态</h2>
      <div class="status-info">
        <p><strong>训练任务ID:</strong> {{ trainingJobId }}</p>
        <p><strong>当前模型:</strong> {{ selectedModel }}</p>
        <p><strong>当前数据集:</strong> {{ selectedDataset }}</p>
      </div>
      
      <div class="logs-container">
        <h3>训练日志</h3>
        <div class="logs">
          <div 
            v-for="(log, index) in logs" 
            :key="index" 
            class="log-entry"
          >
            {{ log }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';

// 数据
const models = ref<string[]>([]);
const datasets = ref<string[]>([]);
const selectedModel = ref<string>('');
const selectedDataset = ref<string>('');
const epochs = ref<number>(100);
const imgSize = ref<number>(640);
const batchSize = ref<number>(16);
const isTraining = ref<boolean>(false);
const trainingJobId = ref<string>('');
const logs = ref<string[]>([]);

// 计算属性
const canStartTraining = computed(() => {
  return selectedModel.value && selectedDataset.value;
});

// 方法
const fetchModels = async () => {
  try {
    const response = await fetch('/api/train/models');
    const data = await response.json();
    models.value = data.models || [];
  } catch (error) {
    console.error('获取模型列表失败:', error);
  }
};

const fetchDatasets = async () => {
  try {
    const response = await fetch('/api/train/datasets');
    const data = await response.json();
    datasets.value = data.datasets || [];
  } catch (error) {
    console.error('获取数据集列表失败:', error);
  }
};

const startTraining = async () => {
  if (!canStartTraining.value) {
    alert('请选择模型和数据集');
    return;
  }
  
  isTraining.value = true;
  
  try {
    const response = await fetch('/api/train/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model_name: selectedModel.value,
        dataset_name: selectedDataset.value,
        epochs: epochs.value,
        imgsz: imgSize.value,
        batch_size: batchSize.value
      })
    });
    
    const result = await response.json();
    
    if (response.ok) {
      trainingJobId.value = result.job_id;
      alert('训练已开始');
      
      // 开始获取训练日志
      await fetchTrainingLogs();
    } else {
      alert(`训练启动失败: ${result.detail || '未知错误'}`);
    }
  } catch (error) {
    console.error('启动训练失败:', error);
    alert(`训练启动失败: ${error}`);
  } finally {
    isTraining.value = false;
  }
};

const fetchTrainingLogs = async () => {
  if (!trainingJobId.value) return;
  
  try {
    const response = await fetch(`/api/train/logs/${trainingJobId.value}`);
    const data = await response.json();
    
    if (response.ok) {
      logs.value = data.logs || [];
      
      // 如果训练还在进行中，继续获取日志
      if (!isTraining.value && data.logs && data.logs.some((log: string) => log.includes('Training completed'))) {
        isTraining.value = false;
      } else if (isTraining.value) {
        // 递归调用以持续获取日志
        setTimeout(fetchTrainingLogs, 2000);
      }
    }
  } catch (error) {
    console.error('获取训练日志失败:', error);
    
    // 如果还在训练中，继续尝试获取日志
    if (isTraining.value) {
      setTimeout(fetchTrainingLogs, 2000);
    }
  }
};

// 生命周期
onMounted(() => {
  fetchModels();
  fetchDatasets();
});
</script>

<style scoped>
.train-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.train-form {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-control:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.training-status {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
}

.status-info {
  margin-bottom: 20px;
}

.logs-container {
  margin-top: 20px;
}

.logs {
  background: #000;
  color: #0f0;
  padding: 10px;
  border-radius: 4px;
  height: 300px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.log-entry {
  margin-bottom: 5px;
  white-space: pre-wrap;
}
</style>
