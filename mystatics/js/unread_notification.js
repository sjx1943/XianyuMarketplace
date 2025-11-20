// 未读消息通知系统
(function() {
    'use strict';
    
    const unreadCountElement = document.getElementById('unread-count');
    const myMessagesLink = document.getElementById('my-messages-link');
    
    if (!unreadCountElement || !myMessagesLink) {
        console.warn('未读消息元素未找到');
        return;
    }
    
    // 获取未读消息数量
    async function fetchUnreadCount() {
        try {
            const response = await fetch('/api/unread_count', {
                method: 'GET',
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('获取未读消息失败');
            }
            
            const data = await response.json();
            updateUnreadDisplay(data.total_unread || 0);
        } catch (error) {
            console.error('获取未读消息数量失败:', error);
        }
    }
    
    // 更新未读消息显示
    function updateUnreadDisplay(count) {
        if (count > 0) {
            unreadCountElement.textContent = count > 99 ? '99+' : count;
            unreadCountElement.style.display = 'block';
            
            // 添加震动动画效果
            unreadCountElement.classList.add('pulse');
            setTimeout(() => {
                unreadCountElement.classList.remove('pulse');
            }, 1000);
        } else {
            unreadCountElement.style.display = 'none';
        }
    }
    
    // 页面加载时立即获取一次
    fetchUnreadCount();
    
    // 每15秒自动更新一次
    setInterval(fetchUnreadCount, 15000);
    
    // 当用户回到页面时也更新
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            fetchUnreadCount();
        }
    });
    
    // 当点击消息按钮时，延迟1秒后更新（给足够时间标记已读）
    myMessagesLink.addEventListener('click', function() {
        setTimeout(fetchUnreadCount, 1000);
    });
})();

// 卖家未读订单通知系统
(function() {
    'use strict';
    
    const unreadOrdersCountElement = document.getElementById('unread-orders-count');
    
    if (!unreadOrdersCountElement) {
        console.warn('未读订单元素未找到');
        return;
    }
    
    // 获取卖家未读订单数量
    async function fetchUnreadOrdersCount() {
        try {
            const response = await fetch('/api/unread_orders_count', {
                method: 'GET',
                credentials: 'include'
            });
            
            if (!response.ok) {
                throw new Error('获取未读订单失败');
            }
            
            const data = await response.json();
            updateUnreadOrdersDisplay(data.count || 0);
        } catch (error) {
            console.error('获取未读订单数量失败:', error);
        }
    }
    
    // 更新未读订单显示
    function updateUnreadOrdersDisplay(count) {
        if (count > 0) {
            unreadOrdersCountElement.textContent = count > 99 ? '99+' : count;
            unreadOrdersCountElement.style.display = 'block';
            
            // 添加震动动画效果
            unreadOrdersCountElement.classList.add('pulse');
            setTimeout(() => {
                unreadOrdersCountElement.classList.remove('pulse');
            }, 1000);
        } else {
            unreadOrdersCountElement.style.display = 'none';
        }
    }
    
    // 页面加载时立即获取一次
    fetchUnreadOrdersCount();
    
    // 每15秒自动更新一次
    setInterval(fetchUnreadOrdersCount, 15000);
    
    // 当用户回到页面时也更新
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            fetchUnreadOrdersCount();
        }
    });
})();
