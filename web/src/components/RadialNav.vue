<template>
  <div class="radial-nav-container">
    <!-- 中心按钮 -->
    <button 
      @click="toggleMenu" 
      class="center-button"
      :class="{ active: isMenuOpen }"
    >
      <svg 
        class="icon" 
        viewBox="0 0 24 24" 
        fill="none" 
        stroke="currentColor" 
        stroke-width="2"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="16" />
        <line x1="8" y1="12" x2="16" y2="12" />
      </svg>
    </button>

    <!-- 导航项 -->
    <transition name="fade">
      <div v-if="isMenuOpen" class="nav-items">
        <router-link
          v-for="(item, index) in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :style="getItemStyle(index)"
          @click="closeMenu"
        >
          <div class="nav-item-content">
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </div>
        </router-link>
      </div>
    </transition>

    <!-- 背景遮罩 -->
    <transition name="fade">
      <div 
        v-if="isMenuOpen" 
        class="backdrop" 
        @click="closeMenu"
      ></div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface NavItem {
  label: string
  path: string
  icon: string
}

const isMenuOpen = ref(false)

const navItems: NavItem[] = [
  { label: '视频截取', path: '/capture', icon: '🎬' },
  { label: '标注', path: '/annotate', icon: '✏️' },
  { label: '训练', path: '/train', icon: '🚀' },
  { label: '设置', path: '/settings', icon: '⚙️' },
]

const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value
}

const closeMenu = () => {
  isMenuOpen.value = false
}

// 计算导航项的圆形分布位置
const getItemStyle = (index: number) => {
  const total = navItems.length
  const angle = (360 / total) * index - 90 // -90 让第一个项从顶部开始
  const radius = 120 // 圆形半径
  
  const radian = (angle * Math.PI) / 180
  const x = Math.cos(radian) * radius
  const y = Math.sin(radian) * radius
  
  return {
    transform: `translate(${x}px, ${y}px)`,
    transitionDelay: `${index * 50}ms`,
  }
}
</script>

<style scoped>
.radial-nav-container {
  position: fixed;
  bottom: 30px;
  right: 30px;
  z-index: 1000;
}

.center-button {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff8c42, #ffa500);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(255, 140, 66, 0.4);
  transition: all 0.3s ease;
  position: relative;
  z-index: 1002;
}

.center-button:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 25px rgba(255, 140, 66, 0.6);
}

.center-button.active {
  background: linear-gradient(135deg, #4ade80, #22c55e);
  transform: rotate(45deg);
}

.center-button .icon {
  width: 30px;
  height: 30px;
  color: white;
  transition: transform 0.3s ease;
}

.center-button.active .icon {
  transform: rotate(-45deg);
}

.backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 999;
}

.nav-items {
  position: absolute;
  bottom: 30px;
  right: 30px;
  z-index: 1001;
}

.nav-item {
  position: absolute;
  bottom: 0;
  right: 0;
  transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

.nav-item-content {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4ade80, #10b981);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(74, 222, 128, 0.4);
  transition: all 0.3s ease;
  text-decoration: none;
}

.nav-item:hover .nav-item-content {
  transform: scale(1.15);
  box-shadow: 0 6px 20px rgba(74, 222, 128, 0.6);
  background: linear-gradient(135deg, #ff8c42, #ffa500);
}

.nav-icon {
  font-size: 24px;
}

.nav-label {
  font-size: 11px;
  color: white;
  font-weight: 600;
  text-align: center;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .radial-nav-container {
    bottom: 20px;
    right: 20px;
  }

  .center-button {
    width: 50px;
    height: 50px;
  }

  .center-button .icon {
    width: 24px;
    height: 24px;
  }

  .nav-item-content {
    width: 60px;
    height: 60px;
  }

  .nav-icon {
    font-size: 20px;
  }

  .nav-label {
    font-size: 10px;
  }
}
</style>
