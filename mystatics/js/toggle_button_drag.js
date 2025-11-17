// 侧边栏折叠按钮拖拽功能
document.addEventListener('DOMContentLoaded', function() {
    const toggleButton = document.getElementById('toggle-friend-list');
    if (!toggleButton) return;

    let isDragging = false;
    let startX, startY, startLeft, startTop;
    let clickTimeout;
    let hasMoved = false;

    // 设置初始位置（如果没有保存的位置）
    const savedLeft = localStorage.getItem('toggleButtonLeft');
    const savedTop = localStorage.getItem('toggleButtonTop');
    
    if (savedLeft && savedTop) {
        toggleButton.style.left = savedLeft + 'px';
        toggleButton.style.top = savedTop + 'px';
    } else {
        // 默认位置：左上角
        toggleButton.style.left = '10px';
        toggleButton.style.top = '10px';
    }

    // 确保按钮是absolute定位
    toggleButton.style.position = 'fixed';
    toggleButton.style.cursor = 'move';

    // 鼠标按下
    toggleButton.addEventListener('mousedown', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        hasMoved = false;
        isDragging = true;
        
        startX = e.clientX;
        startY = e.clientY;
        startLeft = toggleButton.offsetLeft;
        startTop = toggleButton.offsetTop;
        
        toggleButton.style.cursor = 'grabbing';
        document.body.style.userSelect = 'none';
    });

    // 鼠标移动
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;

        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        // 如果移动超过5px，认为是拖拽
        if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
            hasMoved = true;
        }

        if (hasMoved) {
            let newLeft = startLeft + dx;
            let newTop = startTop + dy;

            // 边界限制
            const maxLeft = window.innerWidth - toggleButton.offsetWidth - 10;
            const maxTop = window.innerHeight - toggleButton.offsetHeight - 10;

            newLeft = Math.max(10, Math.min(newLeft, maxLeft));
            newTop = Math.max(10, Math.min(newTop, maxTop));

            toggleButton.style.left = newLeft + 'px';
            toggleButton.style.top = newTop + 'px';
        }
    });

    // 鼠标释放
    document.addEventListener('mouseup', function(e) {
        if (!isDragging) return;

        isDragging = false;
        toggleButton.style.cursor = 'move';
        document.body.style.userSelect = '';

        if (hasMoved) {
            // 保存位置到localStorage
            localStorage.setItem('toggleButtonLeft', toggleButton.offsetLeft);
            localStorage.setItem('toggleButtonTop', toggleButton.offsetTop);
            
            // 如果是拖拽，阻止点击事件
            e.stopPropagation();
        } else {
            // 如果是点击（没有拖拽），触发折叠/展开
            toggleFriendList();
        }
    });

    // 触摸事件支持（移动端）
    toggleButton.addEventListener('touchstart', function(e) {
        e.preventDefault();
        hasMoved = false;
        isDragging = true;
        
        const touch = e.touches[0];
        startX = touch.clientX;
        startY = touch.clientY;
        startLeft = toggleButton.offsetLeft;
        startTop = toggleButton.offsetTop;
    }, { passive: false });

    document.addEventListener('touchmove', function(e) {
        if (!isDragging) return;

        const touch = e.touches[0];
        const dx = touch.clientX - startX;
        const dy = touch.clientY - startY;

        if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
            hasMoved = true;
        }

        if (hasMoved) {
            e.preventDefault();
            let newLeft = startLeft + dx;
            let newTop = startTop + dy;

            const maxLeft = window.innerWidth - toggleButton.offsetWidth - 10;
            const maxTop = window.innerHeight - toggleButton.offsetHeight - 10;

            newLeft = Math.max(10, Math.min(newLeft, maxLeft));
            newTop = Math.max(10, Math.min(newTop, maxTop));

            toggleButton.style.left = newLeft + 'px';
            toggleButton.style.top = newTop + 'px';
        }
    }, { passive: false });

    document.addEventListener('touchend', function(e) {
        if (!isDragging) return;

        isDragging = false;

        if (hasMoved) {
            localStorage.setItem('toggleButtonLeft', toggleButton.offsetLeft);
            localStorage.setItem('toggleButtonTop', toggleButton.offsetTop);
        } else {
            toggleFriendList();
        }
    });

    // 折叠/展开好友列表
    function toggleFriendList() {
        const friendList = document.querySelector('.friend-list');
        if (friendList) {
            friendList.classList.toggle('collapsed');
        }
    }
});
