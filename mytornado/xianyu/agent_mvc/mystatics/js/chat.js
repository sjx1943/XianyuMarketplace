let currentFriendId = null;
let chatPollingInterval = null;
let longPressTimer = null;

// --- Utility Functions ---
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function scrollToBottom(smooth = false) {
    const container = document.getElementById('message-content-container');
    if (container) {
        if (smooth) {
            container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
        } else {
            container.scrollTop = container.scrollHeight;
        }
    }
}

function showNewMessageNotification() {
    let notification = document.getElementById('new-message-notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'new-message-notification';
        notification.textContent = '↓ 新消息';
        notification.style.cssText = `
            position: absolute;
            bottom: 10px;
            right: 20px;
            background-color: #007bff;
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            cursor: pointer;
            z-index: 100;
            display: none;
        `;
        document.querySelector('.message-area').appendChild(notification);
        notification.addEventListener('click', () => {
            scrollToBottom(true);
            notification.style.display = 'none';
        });
    }
    notification.style.display = 'block';
}

function hideNewMessageNotification() {
    const notification = document.getElementById('new-message-notification');
    if (notification) {
        notification.style.display = 'none';
    }
}

// --- Core Application Logic ---
document.addEventListener('DOMContentLoaded', function() {
    window.currentUserId = parseInt(document.body.getAttribute('data-user-id')) || null;
    initEventListeners();
    const urlParams = new URLSearchParams(window.location.search);
    const friendId = urlParams.get('friend_id');
    if (friendId) {
        const friendElement = document.querySelector(`.friend-item[data-friend-id="${friendId}"]`);
        if (friendElement) selectFriend(friendId, friendElement);
    }
});

function initEventListeners() {
    document.getElementById('send-button')?.addEventListener('click', sendMessage);
    document.getElementById('message-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); sendMessage(); }
    });

    document.querySelectorAll('.friend-item').forEach(item => {
        item.addEventListener('click', function() {
            selectFriend(this.dataset.friendId, this);
        });
    });

    document.getElementById('toggle-friend-list')?.addEventListener('click', () => {
        document.getElementById('friend-list-container').classList.toggle('collapsed');
    });

    const container = document.getElementById('message-content-container');
    if (container) {
        container.addEventListener('scroll', () => {
            if (container.scrollHeight - container.clientHeight <= container.scrollTop + 1) {
                hideNewMessageNotification();
            }
        }, { passive: true });
    }

    initFriendListContextMenu();
    initMessageContextMenu();
    initAutoResizeAndDrag(); // Initialize new features
}

function initAutoResizeAndDrag() {
    const friendList = document.getElementById('friend-list-container');
    const dragHandle = document.getElementById('drag-handle');
    const BREAKPOINT = 992; // Bootstrap's lg breakpoint

    // Debounce function to limit resize event firing
    function debounce(func, delay) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Auto-collapse based on window size
    const handleResize = () => {
        if (window.innerWidth < BREAKPOINT) {
            friendList.classList.add('collapsed');
        } else {
            friendList.classList.remove('collapsed');
        }
    };

    window.addEventListener('resize', debounce(handleResize, 100));
    handleResize(); // Initial check

    // Drag-to-resize logic
    if (dragHandle) {
        dragHandle.addEventListener('mousedown', function(e) {
            e.preventDefault();
            document.body.classList.add('is-resizing');

            const startX = e.clientX;
            const startWidth = friendList.offsetWidth;

            const doDrag = function(e) {
                const newWidth = startWidth + e.clientX - startX;
                // Get min/max from CSS properties
                const minWidth = parseInt(window.getComputedStyle(friendList).minWidth, 10);
                const maxWidth = parseInt(window.getComputedStyle(friendList).maxWidth, 10);

                if (newWidth > minWidth && newWidth < maxWidth) {
                    friendList.style.width = `${newWidth}px`;
                }
            };

            const stopDrag = function() {
                document.body.classList.remove('is-resizing');
                document.removeEventListener('mousemove', doDrag);
                document.removeEventListener('mouseup', stopDrag);
            };

            document.addEventListener('mousemove', doDrag);
            document.addEventListener('mouseup', stopDrag);
        });
    }
}

function selectFriend(friendId, element) {
    currentFriendId = friendId;
    document.querySelectorAll('.friend-item').forEach(item => item.classList.remove('active'));
    element.classList.add('active');
    document.getElementById('no-chat-message').style.display = 'none';
    document.getElementById('message-content').style.display = 'block';
    document.getElementById('message-input-area').style.display = 'flex';

    loadMessages(friendId).then(() => {
        markMessagesRead(friendId);
        scrollToBottom(); // When selecting a friend, always scroll to the bottom.
        startChatPolling();
    });
}

function startChatPolling() {
    if (chatPollingInterval) clearInterval(chatPollingInterval);
    fetchNewData();
    chatPollingInterval = setInterval(fetchNewData, 3000);
}

function fetchNewData() {
    if (!window.currentUserId) return;
    fetch(`/api/unread_count`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                updateUnreadIndicators(data.counts || {});
                if ((data.counts[currentFriendId] || 0) > 0) {
                    fetchNewMessagesForCurrentChat();
                }
            }
        });
}

function fetchNewMessagesForCurrentChat() {
    if (!currentFriendId) return;

    loadMessages(currentFriendId).then(() => {
        markMessagesRead(currentFriendId);
        scrollToBottom(true); // Always scroll to bottom smoothly on new message
    });
}

function loadMessages(friendId) {
    const messageContent = document.getElementById('message-content');
    return fetch(`/api/messages?friend_id=${friendId}`)
        .then(response => response.json())
        .then(messages => {
            messageContent.innerHTML = '';
            if (!messages || messages.length === 0) {
                messageContent.innerHTML = '<div class="no-messages">暂无消息</div>';
            } else {
                messages.forEach(msg => {
                    const isSelf = msg.from_user_id == window.currentUserId;
                    appendMessage(isSelf ? '我' : msg.from_username, msg.message, isSelf, msg.timestamp, msg._id);
                });
            }
            // Ensure we scroll to the bottom after messages are loaded and rendered
            setTimeout(() => scrollToBottom(), 0);
        });
}

function appendMessage(sender, content, isSelf, timestamp, messageId) {
    const messageContent = document.getElementById('message-content');
    // 如果消息已经存在，则不重复添加
    if (!messageContent || document.querySelector(`.message[data-message-id="${messageId}"]`)) return;

    const noMessages = messageContent.querySelector('.no-messages');
    if (noMessages) noMessages.remove();

    // 创建一个包裹层来处理对齐
    const msgWrapper = document.createElement('div');
    msgWrapper.className = isSelf ? 'message-wrapper sent' : 'message-wrapper received';
    
    // 创建消息气泡本身
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message';
    msgDiv.dataset.messageId = messageId;

    // 创建消息文本内容
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-text';
    contentDiv.textContent = content; // 使用 textContent 来防止XSS

    // 创建时间戳
    const timeSpan = document.createElement('span');
    timeSpan.className = 'message-time';
    // 格式化时间戳，只显示时和分
    try {
        const date = new Date(timestamp);
        if (!isNaN(date)) {
            timeSpan.textContent = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        } else {
            timeSpan.textContent = timestamp; // 如果格式不对，显示原始字符串
        }
    } catch (e) {
        timeSpan.textContent = timestamp; // 解析出错，显示原始字符串
    }

    msgDiv.appendChild(contentDiv);
    msgDiv.appendChild(timeSpan);
    msgWrapper.appendChild(msgDiv);
    
    messageContent.appendChild(msgWrapper);
}

function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    if (!message || !currentFriendId) return;

    fetch('/api/send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-XSRFToken': getCookie('_xsrf') },
        body: JSON.stringify({ friend_id: currentFriendId, message: message })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            messageInput.value = '';
            fetchNewMessagesForCurrentChat();
        } else {
            alert(data.error || '消息发送失败');
        }
    });
}

function markMessagesRead(friendId) {
    fetch('/api/mark_messages_read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-XSRFToken': getCookie('_xsrf') },
        body: JSON.stringify({ friend_id: friendId })
    }).then(() => updateUnreadIndicators({}));
}

function updateUnreadIndicators(counts) {
    document.querySelectorAll('.friend-item').forEach(item => {
        const friendId = item.dataset.friendId;
        const count = counts[friendId] || 0;
        const redDot = item.querySelector('.red-dot');
        if (redDot) redDot.style.display = count > 0 ? 'inline-block' : 'none';
    });
}

// --- Context Menu Logic ---

function initMessageContextMenu() {
    const contextMenu = document.getElementById('message-context-menu');
    const messageContent = document.getElementById('message-content');

    document.addEventListener('click', () => contextMenu.style.display = 'none');

    messageContent.addEventListener('contextmenu', function(e) {
        const targetMessage = e.target.closest('.message');
        if (targetMessage) {
            e.preventDefault();
            targetMessage.classList.toggle('selected');
            
            // Calculate menu position based on message element and container boundaries
            const messageRect = targetMessage.getBoundingClientRect();
            const containerRect = messageContent.getBoundingClientRect();
            
            // Default to right side of message
            let menuLeft = messageRect.right + 5;
            
            // Check if menu would go beyond right boundary
            if (menuLeft + contextMenu.offsetWidth > containerRect.right) {
                // Position menu to the left of message instead
                menuLeft = messageRect.left - contextMenu.offsetWidth - 5;
            }
            
            // Ensure menu stays within container horizontally
            menuLeft = Math.max(containerRect.left, Math.min(menuLeft, containerRect.right - contextMenu.offsetWidth));
            
            // Position menu vertically at center of message
            let menuTop = messageRect.top + (messageRect.height / 2) - (contextMenu.offsetHeight / 2);
            
            // Ensure menu stays within container vertically
            menuTop = Math.max(containerRect.top, Math.min(menuTop, containerRect.bottom - contextMenu.offsetHeight));
            
            contextMenu.style.display = 'block';
            contextMenu.style.left = `${menuLeft}px`;
            contextMenu.style.top = `${menuTop}px`;
        }
    });

    document.getElementById('delete-selected')?.addEventListener('click', deleteSelectedMessages);
    document.getElementById('delete-all')?.addEventListener('click', deleteAllMessages);
}

function initFriendListContextMenu() {
    const contextMenu = document.getElementById('friend-context-menu');
    const friendListContainer = document.getElementById('friend-list-container');
    let currentTargetFriendId = null;

    const showMenu = (e) => {
        const targetFriend = e.target.closest('.friend-item');
        if (!targetFriend) return;
        
        e.preventDefault();
        e.stopPropagation();

        currentTargetFriendId = targetFriend.dataset.friendId;
        const status = targetFriend.dataset.status;

        const blockOption = document.getElementById('friend-menu-block');
        blockOption.textContent = status === 'blocked' ? '取消拉黑' : '拉黑';

        contextMenu.style.display = 'block';
        contextMenu.style.left = `${e.pageX}px`;
        contextMenu.style.top = `${e.pageY}px`;
    };

    friendListContainer.addEventListener('contextmenu', showMenu);

    // Mobile long-press support
    friendListContainer.addEventListener('touchstart', (e) => {
        const targetFriend = e.target.closest('.friend-item');
        if (!targetFriend) return;
        longPressTimer = setTimeout(() => {
            showMenu(e);
        }, 500); // 500ms for long press
    });

    friendListContainer.addEventListener('touchend', () => clearTimeout(longPressTimer));
    friendListContainer.addEventListener('touchmove', () => clearTimeout(longPressTimer));

    document.addEventListener('click', () => contextMenu.style.display = 'none');

    document.getElementById('friend-menu-profile')?.addEventListener('click', () => {
        if (currentTargetFriendId) window.location.href = `/profile/${currentTargetFriendId}`;
    });
    document.getElementById('friend-menu-block')?.addEventListener('click', () => {
        if (currentTargetFriendId) blockFriend(currentTargetFriendId);
    });
    document.getElementById('friend-menu-delete')?.addEventListener('click', () => {
        if (currentTargetFriendId) deleteFriend(currentTargetFriendId);
    });
}


function deleteSelectedMessages() {
    const selected = document.querySelectorAll('.message.selected');
    if (selected.length === 0) return;
    if (confirm(`确定删除选中的 ${selected.length} 条消息吗？`)) {
        const messageIds = Array.from(selected).map(msg => msg.dataset.messageId);
        deleteMessagesFromServer(messageIds);
    }
}

function deleteAllMessages() {
    if (confirm(`确定删除与该好友的所有聊天记录吗？`)) {
        const allMessages = document.querySelectorAll('.message');
        const messageIds = Array.from(allMessages).map(msg => msg.dataset.messageId);
        deleteMessagesFromServer(messageIds);
    }
}

function deleteMessagesFromServer(messageIds) {
    if (messageIds.length === 0) return;
    fetch('/api/delete_messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-XSRFToken': getCookie('_xsrf') },
        body: JSON.stringify({ message_ids: messageIds, friend_id: currentFriendId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            messageIds.forEach(id => {
                document.querySelector(`.message[data-message-id="${id}"]`)?.remove();
            });
            // Reload messages for current friend instead of showing "暂无消息"
            if (currentFriendId) {
                loadMessages(currentFriendId);
            }
        }
    });
}

// --- Friend Management Functions ---

function deleteFriend(friendId) {
    if (!confirm('确定要删除该好友吗？删除后聊天记录也将清空。')) return;

    fetch('/api/delete_friend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-XSRFToken': getCookie('_xsrf') },
        body: JSON.stringify({ friend_id: friendId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('好友删除成功');
            const friendElement = document.querySelector(`.friend-item[data-friend-id="${friendId}"]`);
            friendElement?.remove();
            if (currentFriendId === friendId) {
                document.getElementById('message-content').innerHTML = '<div class="no-chat-selected" id="no-chat-message">未选择聊天</div>';
                document.getElementById('message-input-area').style.display = 'none';
                stopChatPolling();
                currentFriendId = null;
            }
        } else {
            alert('删除失败: ' + data.message);
        }
    });
}

function blockFriend(friendId) {
    const friendElement = document.querySelector(`.friend-item[data-friend-id="${friendId}"]`);
    const currentStatus = friendElement.dataset.status;
    const actionText = currentStatus === 'blocked' ? '取消拉黑' : '拉黑';

    if (!confirm(`确定要${actionText}该好友吗？`)) return;

    fetch('/api/block_friend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-XSRFToken': getCookie('_xsrf') },
        body: JSON.stringify({ friend_id: friendId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert(data.message);
            // Toggle status on the element
            const newStatus = currentStatus === 'blocked' ? 'active' : 'blocked';
            friendElement.dataset.status = newStatus;
        } else {
            alert(`${actionText}失败: ` + data.message);
        }
    });
}