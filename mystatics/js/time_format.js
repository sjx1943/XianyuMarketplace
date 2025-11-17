// 时间格式化工具 - 支持北京时间（东8区）
function formatRelativeTime(timestamp) {
    const now = new Date();
    
    // 处理时间戳：如果是 "YYYY-MM-DD HH:MM:SS" 格式（来自后端）
    // 替换空格为T以兼容Safari，并确保解析为北京时间
    let past;
    if (typeof timestamp === 'string' && timestamp.includes(' ')) {
        // 后端返回的北京时间格式："2025-11-17 12:30:00"
        // 替换为ISO格式便于解析
        past = new Date(timestamp.replace(' ', 'T'));
    } else {
        past = new Date(timestamp);
    }
    
    // 如果解析失败，返回原始时间戳
    if (isNaN(past.getTime())) {
        return timestamp;
    }
    
    const diffMs = now - past;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) {
        return '刚刚';
    } else if (diffMin < 60) {
        return `${diffMin}分钟前`;
    } else if (diffHour < 24) {
        return `${diffHour}小时前`;
    } else if (diffDay < 7) {
        return `${diffDay}天前`;
    } else {
        // 超过7天显示完整日期
        return timestamp.substring(0, 16).replace('T', ' ');
    }
}

// 将所有时间戳转换为相对时间
function updateAllTimestamps() {
    document.querySelectorAll('.timestamp, .message-time, .comment-time, .broadcast-time').forEach(el => {
        const originalTime = el.dataset.time || el.textContent.trim();
        if (originalTime) {
            el.dataset.time = originalTime;  // 保存原始时间
            el.textContent = formatRelativeTime(originalTime);
            el.title = `${originalTime} (北京时间)`;  // 鼠标悬停显示完整时间
        }
    });
}

// 页面加载完成后更新时间戳
document.addEventListener('DOMContentLoaded', updateAllTimestamps);

// 每分钟更新一次相对时间
setInterval(updateAllTimestamps, 60000);
