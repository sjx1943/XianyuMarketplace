// 搜索功能实现
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const searchResults = document.getElementById('search-results');

    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const query = searchInput.value.trim();
            if (query) {
                performSearch(query);
            }
        });
    }

    if (searchButton) {
        searchButton.addEventListener('click', function(e) {
            e.preventDefault();
            const query = searchInput.value.trim();
            if (query) {
                performSearch(query);
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const query = searchInput.value.trim();
                if (query) {
                    performSearch(query);
                }
            }
        });
    }
});

// 执行搜索
function performSearch(query) {
    const productListDiv = document.getElementById('product-list');
    const searchResults = document.getElementById('search-results');

    // 显示加载状态
    searchResults.innerHTML = '<p>正在搜索...</p>';

    fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('搜索请求失败，请稍后重试');
            }
            return response.json();
        })
        .then(products => {
            // 清空搜索结果容器
            searchResults.innerHTML = '';

            // 更新主界面产品列表
            updateProductList(products);

            // 如果没有搜索结果
            if (products.length === 0) {
                searchResults.innerHTML = '<p>没有找到相关商品</p>';
            } else {
                // 显示搜索结果数量
                searchResults.innerHTML = `<p>找到 ${products.length} 个相关商品</p>`;
                // 3秒后自动隐藏搜索结果提示
                setTimeout(() => {
                    searchResults.innerHTML = '';
                }, 3000);
            }
        })
        .catch(error => {
            console.error('搜索错误:', error);
            searchResults.innerHTML = `<p class="error-msg">${error.message}</p>`;

            // 5秒后自动隐藏错误信息
            setTimeout(() => {
                searchResults.innerHTML = '';
            }, 5000);
        });
}

// 更新产品列表
function updateProductList(products) {
    const productListDiv = document.getElementById('product-list');
    if (!productListDiv) return;

    productListDiv.innerHTML = '';

    // 添加无商品提示
    if (products.length === 0) {
        productListDiv.innerHTML = '<p class="no-products">暂无相关商品</p>';
        return;
    }

    // 获取当前登录用户ID
    const loggedInUserIdElement = document.getElementById('logged-in-user-id');
    const currentUserId = loggedInUserIdElement ? parseInt(loggedInUserIdElement.value) : null;

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
                ${currentUserId && product.user_id === currentUserId ? 
                  `<button class="edit-product" data-id="${product.id}">编辑</button>` : ''}
            </div>
        `;
        productListDiv.appendChild(productDiv);
    });
}