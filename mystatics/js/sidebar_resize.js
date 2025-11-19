document.addEventListener('DOMContentLoaded', function() {
    const friendList = document.getElementById('friend-list-container');
    const resizer = document.getElementById('drag-handle');
    const toggleBtn = document.getElementById('toggle-friend-list');
    const overlay = document.getElementById('sidebar-overlay');
    const STORAGE_KEY = 'chatroom_sidebar_width';
    const MIN_WIDTH = 200;
    const MAX_WIDTH = 400;
    const DEFAULT_WIDTH = 280;

    let isResizing = false;
    let isMobile = window.innerWidth <= 768;

    function loadSidebarWidth() {
        const savedWidth = localStorage.getItem(STORAGE_KEY);
        if (savedWidth && !isMobile) {
            const width = parseInt(savedWidth, 10);
            if (width >= MIN_WIDTH && width <= MAX_WIDTH) {
                friendList.style.width = `${width}px`;
            }
        }
    }

    function saveSidebarWidth(width) {
        localStorage.setItem(STORAGE_KEY, width.toString());
    }

    function startResize(e) {
        if (isMobile) return;
        isResizing = true;
        document.body.classList.add('is-resizing');
        document.body.style.cursor = 'col-resize';
        e.preventDefault();
    }

    function resize(e) {
        if (!isResizing || isMobile) return;

        const containerRect = friendList.parentElement.getBoundingClientRect();
        const newWidth = e.clientX - containerRect.left;

        if (newWidth >= MIN_WIDTH && newWidth <= MAX_WIDTH) {
            friendList.style.width = `${newWidth}px`;
        }
    }

    function stopResize() {
        if (!isResizing) return;
        isResizing = false;
        document.body.classList.remove('is-resizing');
        document.body.style.cursor = '';

        const currentWidth = parseInt(friendList.style.width || DEFAULT_WIDTH, 10);
        saveSidebarWidth(currentWidth);
    }

    function toggleMobileSidebar() {
        if (!isMobile) return;

        const isVisible = friendList.classList.contains('mobile-visible');
        
        if (isVisible) {
            friendList.classList.remove('mobile-visible');
            overlay.classList.remove('active');
        } else {
            friendList.classList.add('mobile-visible');
            overlay.classList.add('active');
        }
    }

    function handleResize() {
        const wasMobile = isMobile;
        isMobile = window.innerWidth <= 768;

        if (wasMobile !== isMobile) {
            if (isMobile) {
                // Switching from desktop to mobile
                friendList.classList.remove('mobile-visible');
                overlay.classList.remove('active');
                friendList.style.width = '';
            } else {
                // Switching from mobile to desktop
                friendList.classList.remove('mobile-visible');
                overlay.classList.remove('active');
                loadSidebarWidth();
            }
        } else if (isMobile) {
            // Still mobile, ensure sidebar is hidden on orientation change
            friendList.classList.remove('mobile-visible');
            overlay.classList.remove('active');
        }
    }

    if (resizer) {
        resizer.addEventListener('mousedown', startResize);
        document.addEventListener('mousemove', resize);
        document.addEventListener('mouseup', stopResize);
    }

    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleMobileSidebar);
    }

    if (overlay) {
        overlay.addEventListener('click', function() {
            if (isMobile) {
                toggleMobileSidebar();
            }
        });
    }

    window.addEventListener('resize', handleResize);

    loadSidebarWidth();
});
