// 获取URL参数
const urlParams = new URLSearchParams(window.location.search);
const userIdFromUrl = parseInt(urlParams.get('user_id'));

// DOM元素
const productListDiv = document.getElementById('product-list');

// 修改获取当前用户ID的逻辑
//window.currentUserId = document.body.getAttribute('data-user-id') || userIdFromUrl;
const loggedInUserId = document.getElementById('logged-in-user-id');
window.currentUserId = loggedInUserId ? parseInt(loggedInUserId.value) : null;

// 加载商品信息
function loadProducts(tag = 'all') {
    const productListDiv = document.getElementById('product-list');
    if (!productListDiv) {
        console.error('Product list div not found');
        return;
    }
    // 使用fetch API替代XMLHttpRequest
    fetch(`/product_list${tag && tag !== 'all' ? `?tag=${tag}` : ''}`)
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(products => {
            productListDiv.innerHTML = '';

            // 添加无商品提示
            if (products.length === 0) {
                productListDiv.innerHTML = '<p class="no-products">暂无相关商品</p>';
                return;
            }

            products.forEach(product => {
                const productDiv = document.createElement('div');
                productDiv.className = 'product-item';
                productDiv.innerHTML = `
                    <div class="product-info">
                        <a href="/product/detail/${product.id}">
                            <img src="/static/images/${product.image}" alt="${product.name}">
                        </a>
                        <h2>${product.name}</h2>
                        <p>￥${product.price}</p>
                        <p>数量：${product.quantity}</p>
                        <p>标签：${product.tag}</p>
                        <p>商品上传者ID：${product.user_id}</p>
                        ${window.currentUserId ? `<p>当前用户ID：${window.currentUserId}</p>` : ''}
                        ${product.user_id === window.currentUserId ?
                          `<a href="/product/edit/${product.id}" class="edit-product button-link">编辑</a>` : ''}
                    </div>
                `;
                productListDiv.appendChild(productDiv);
            });

            // 更新活跃标签样式
            updateActiveTag(tag);
        })
        .catch(error => {
            console.error('加载商品失败:', error);
            productListDiv.innerHTML =
                '<p class="error-msg">加载商品失败，请稍后重试</p>';
        });
}

// 添加好友功能
function setupAddFriendButton() {
    const addFriendBtn = document.getElementById('add-friend-btn');
    if (!addFriendBtn) return;

    addFriendBtn.addEventListener('click', async function() {
        const friendId = parseInt(this.dataset.friendId);
        const loggedInUserId = document.getElementById('logged-in-user-id');
        const currentUserId = loggedInUserId ? parseInt(loggedInUserId.value) : null;

        if (!currentUserId) {
            alert('请先登录后再添加好友');
            return;
        }

        try {
            const response = await fetch('/friend_profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('_xsrf')
                },
                body: JSON.stringify({
                    user_id: currentUserId,
                    friend_id: friendId
                })
            });

            const result = await response.json();
            if (result.success) {
                alert('好友添加成功！');
            } else {
                alert(result.message || '添加好友失败');
            }
        } catch (error) {
            console.error('添加好友出错:', error);
            alert('添加好友时出错');
        }
    });
}

// 获取Cookie的辅助函数
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}


// 更新活跃标签样式
function updateActiveTag(tag) {
    document.querySelectorAll('.category-nav a').forEach(link => {
        link.classList.toggle('active', link.dataset.tag === tag);
    });
}

// 获取未读消息数量
async function getUnreadMessageCount() {
    // 确保 currentUserId 已定义且有效
    if (!window.currentUserId) {
        // console.log("User ID not available for unread count check.");
        return;
    }
    try {
        const response = await fetch('/api/unread_count');
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        if (data.status !== 'success') {
            console.error('Failed to get unread counts:', data.error);
            return;
        }

        const totalUnread = data.total_count || 0;
        const unreadCountElement = document.getElementById('unread-count');

        // 更新底部菜单的全局角标
        if (unreadCountElement) {
            if (totalUnread > 0) {
                unreadCountElement.textContent = totalUnread;
                unreadCountElement.style.display = 'inline-block';
            } else {
                unreadCountElement.style.display = 'none';
            }
        }

        // 发出一个全局事件，携带每个好友的未读数量
        // 供 chat.js 监听以更新好友列表的红点
        const event = new CustomEvent('unreadCountsUpdated', { detail: data.counts || {} });
        document.dispatchEvent(event);

    } catch (error) {
        console.error('获取未读消息数量失败:', error);
    }
}

// 处理新消息事件 (这个可以移除，因为我们现在是定时轮询)
// function handleNewMessage() {
//     getUnreadMessageCount();
// }

// 监听新消息自定义事件 (这个可以移除)
// document.addEventListener('newMessage', handleNewMessage);

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    // 立即执行一次以获取初始计数
    getUnreadMessageCount();

    // 商品列表加载逻辑 - 修改为检查main_page路径
    if (document.getElementById('product-list') &&
        (window.location.pathname === '/' ||
         window.location.pathname.includes('main') ||
         window.location.pathname.includes('home_page') ||
         window.location.pathname.includes('else_home_page'))) {
        loadProducts();
    }
    
    // ... (rest of the DOMContentLoaded logic)
});

