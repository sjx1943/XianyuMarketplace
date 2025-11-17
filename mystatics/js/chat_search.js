// 聊天室搜索功能
document.addEventListener('DOMContentLoaded', function() {
    const searchBar = document.querySelector('.search-bar');
    const messageContent = document.getElementById('message-content');
    let searchResults = [];
    let currentSearchIndex = -1;

    if (!searchBar) return;

    // 监听搜索输入
    searchBar.addEventListener('input', function(e) {
        const query = e.target.value.trim().toLowerCase();
        
        // 清除之前的高亮
        clearSearchHighlights();
        searchResults = [];
        currentSearchIndex = -1;

        if (query.length === 0) {
            return;
        }

        // 搜索当前聊天记录
        const messages = messageContent.querySelectorAll('.message');
        messages.forEach((msg, index) => {
            const messageText = msg.textContent.toLowerCase();
            if (messageText.includes(query)) {
                searchResults.push(msg);
                // 高亮匹配的消息
                msg.classList.add('search-highlight');
            }
        });

        // 如果有搜索结果，滚动到第一个
        if (searchResults.length > 0) {
            currentSearchIndex = 0;
            scrollToSearchResult(0);
            updateSearchStatus();
        } else {
            searchBar.placeholder = '未找到匹配的消息';
            setTimeout(() => {
                searchBar.placeholder = '搜索聊天记录/联系人/服务号';
            }, 2000);
        }
    });

    // Enter键切换到下一个搜索结果
    searchBar.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && searchResults.length > 0) {
            e.preventDefault();
            currentSearchIndex = (currentSearchIndex + 1) % searchResults.length;
            scrollToSearchResult(currentSearchIndex);
            updateSearchStatus();
        }
    });

    function scrollToSearchResult(index) {
        if (index >= 0 && index < searchResults.length) {
            const msg = searchResults[index];
            // 移除之前的活动高亮
            searchResults.forEach(m => m.classList.remove('search-active'));
            // 添加当前高亮
            msg.classList.add('search-active');
            // 滚动到视图
            msg.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    function updateSearchStatus() {
        if (searchResults.length > 0) {
            searchBar.placeholder = `找到 ${searchResults.length} 条消息 (${currentSearchIndex + 1}/${searchResults.length})`;
        }
    }

    function clearSearchHighlights() {
        const highlighted = messageContent.querySelectorAll('.search-highlight, .search-active');
        highlighted.forEach(el => {
            el.classList.remove('search-highlight', 'search-active');
        });
    }

    // 点击外部清除搜索
    document.addEventListener('click', function(e) {
        if (!searchBar.contains(e.target)) {
            clearSearchHighlights();
            searchResults = [];
            currentSearchIndex = -1;
            searchBar.value = '';
            searchBar.placeholder = '搜索聊天记录/联系人/服务号';
        }
    });
});
