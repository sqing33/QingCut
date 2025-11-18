import matplotlib
import matplotlib.font_manager as fm
import os
import logging

# 配置日志
logger = logging.getLogger(__name__)

def configure_matplotlib_fonts():
    """
    配置matplotlib以正确显示中文字体，解决Glyph missing警告
    """
    # 尝试查找系统中的中文字体
    chinese_fonts = []
    
    # 常见的中文字体名称
    preferred_fonts = [
        'SimHei', 'SimSun', 'Microsoft YaHei', 'STHeiti', 
        'Noto Sans CJK', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei',
        'FangSong', 'KaiTi', 'Arial Unicode MS'
    ]
    
    # 获取系统所有可用字体
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    # 查找可用的中文字体
    for font_name in preferred_fonts:
        if font_name in available_fonts:
            chinese_fonts.append(font_name)
    
    # 如果找不到首选字体，尝试查找任何包含中文字形的字体
    if not chinese_fonts:
        for font in fm.fontManager.ttflist:
            # 检查字体名称是否包含中文字体的关键词
            if any(keyword in font.name.lower() for keyword in 
                   ['noto', 'sim', 'yahei', 'hei', 'song', 'kai', 'fang', 'wen']):
                chinese_fonts.append(font.name)
    
    # 设置字体配置
    if chinese_fonts:
        # 使用找到的第一个中文字体
        matplotlib.rcParams['font.sans-serif'] = chinese_fonts
        logger.info(f"设置中文字体: {chinese_fonts[0]}")
    else:
        # 如果找不到中文字体，使用默认字体但允许fallback
        logger.warning("未找到可用的中文字体，可能会出现中文显示问题")
        matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Bitstream Vera Sans']
    
    # 设置其他相关参数
    matplotlib.rcParams['axes.unicode_minus'] = False  # 解决负号'-'显示为方块的问题
    matplotlib.rcParams['font.family'] = 'sans-serif'
    
    logger.info("matplotlib字体配置完成")

# 在模块导入时自动配置
configure_matplotlib_fonts()