// Helper function to get a cookie by name
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

document.addEventListener('DOMContentLoaded', function() {
    // 添加好友
    const addFriendBtn = document.getElementById('add-friend-btn');
    if (addFriendBtn) {
        addFriendBtn.addEventListener('click', function() {
            const friendId = this.dataset.friendId;
            const userId = this.dataset.userId;
            fetch('/api/add_friend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-XSRFToken': getCookie('_xsrf')
                },
                body: JSON.stringify({
                    friend_id: friendId,
                    user_id: userId
                })
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if (data.success) {
                    // Instead of reloading, maybe just change the button state
                    this.textContent = '已是好友';
                    this.disabled = true;
                }
            });
        });
    }

    // 删除好友
    const deleteFriendBtn = document.getElementById('delete-friend-btn');
    if (deleteFriendBtn) {
        deleteFriendBtn.addEventListener('click', function() {
            if (!confirm('确定要删除该好友吗？')) {
                return;
            }
            const friendId = this.dataset.friendId;
            fetch('/api/delete_friend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-XSRFToken': getCookie('_xsrf')
                },
                body: JSON.stringify({
                    friend_id: friendId
                })
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if (data.status === 'success') {
                    window.location.reload();
                }
            });
        });
    }

    // 拉黑/取消拉黑好友
    const blockFriendBtn = document.getElementById('block-friend-btn');
    if (blockFriendBtn) {
        blockFriendBtn.addEventListener('click', function() {
            const friendId = this.dataset.friendId;
            const action = this.textContent.trim() === '拉黑' ? 'block' : 'unblock';
            
            if (!confirm(`确定要${action === 'block' ? '拉黑' : '取消拉黑'}该好友吗？`)) {
                return;
            }

            fetch('/api/block_friend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-XSRFToken': getCookie('_xsrf')
                },
                body: JSON.stringify({
                    friend_id: friendId
                })
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if (data.status === 'success') {
                    this.textContent = action === 'block' ? '取消拉黑' : '拉黑';
                }
            });
        });
    }
});
