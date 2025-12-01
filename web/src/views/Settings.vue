<template>
  <div class="page">
    <!-- <div class="placeholder">
      <h1>⚙️ 设置</h1>
      <p>即将推出</p>
    </div> -->
    <pre class="code-block"><code>
      123</code></pre>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(135deg, #fef3c7 0%, #d1fae5 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.placeholder {
  text-align: center;
  padding: 60px;
  background: white;
  border-radius: 20px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.placeholder h1 {
  font-size: 48px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.placeholder p {
  font-size: 20px;
  color: #666;
}

.code-block {
  font-family: 'Consolas', 'Monaco', monospace; /* 更美观的等宽字体 */
  background: #2d2d2d; /* 深色背景 */
  color: #f8f8f2; /* 浅色文字（代码高亮风格） */
  padding: 1.5rem;
  border-radius: 8px; /* 圆角 */
  overflow-x: auto;
  line-height: 1.6; /* 行高优化 */
}
</style>
