# 小区二手商品交易平台

## Overview
This project is a community-based second-hand goods trading platform built with the Tornado framework, adapted for deployment on Replit. It facilitates the exchange of idle items among residents, focusing on ease of use, security, and a rich user experience. Key features include robust user authentication (password, phone number + SMS, and WeChat OAuth), a real-time chat system, comprehensive product listings with image uploads, and an administrative dashboard for platform management. The platform includes a **WeChat Mini Program** frontend that provides a native mobile experience sharing the same backend API. The platform aims to create a streamlined and trustworthy environment for local community trading with market potential in local community engagement and e-commerce.

## User Preferences
I prefer iterative development with clear, concise explanations for each step. Please prioritize core functionality and user experience. I value clean code and robust error handling. For any significant changes or architectural decisions, please ask for my approval first. Ensure all user-facing features are mobile-responsive and accessible. Do not make changes to folder `base/`. Do not make changes to file `config.ini`.

## System Architecture
The platform is built on Python 3.11 with the Tornado 6.4.2 web framework.

### Development and Production Environment Separation
-   **Development (Replit)**: For coding, testing, and iteration. Uses Replit's PostgreSQL and MongoDB. Runs directly via `python app.py --port=5000`.
-   **Production (VPS)**: For stable online service. Uses RackNerd VPS, Containerd + Docker Compose, and self-deployed PostgreSQL + MongoDB. Deployed with `docker-compose -f docker-compose-prod.yml up -d`.

### Core Technology Stack
-   **Backend**: Python 3.11 + Tornado 6.4.2
-   **ORM**: SQLAlchemy 2.0.28
-   **Relational Database**: PostgreSQL 15 (for user data, products, orders)
-   **NoSQL Database**: MongoDB 7 (for chat messages)
-   **Cache**: Redis 7 (optional)
-   **Container Engine**: Containerd (production)
-   **Web Server**: Nginx (production reverse proxy)
-   **Frontend**:
    -   **Web**: HTML, CSS, JavaScript, WebSockets.
    -   **WeChat Mini Program**: Native WXML, WXSS, JavaScript (`miniprogram/` folder).
-   **UI/UX**: Modern, responsive design with intuitive navigation, including inline error messages, dynamic navigation, mobile-friendly elements, and responsive chat.
-   **Authentication**: Supports username/room number + password, phone + SMS, WeChat OAuth (web and mini program via `wx.login()`).
-   **Session Management**: Per-handler session pattern to prevent cross-request pollution.
-   **Chat System**: Real-time messaging with unread notifications, search, and a draggable, responsive sidebar.
-   **Product Management**: Listing with instant image preview, multi-tag selection, and optimized multi-field search. Features product condition selection.
-   **Order Workflow**: Simplified states (`pending`, `shipped`, `completed`), including seller-side unread notifications and a 24-hour automatic confirmation countdown. Only completed transaction buyers can review.
-   **Admin Dashboard**: Comprehensive interface for user, product, and order management, secured by `is_admin` flag.
-   **Core Concepts**:
    -   **Room Number Identity**: Users identified by a mandatory "room number" (e.g., '3-1-801').
    -   **Time Handling**: All timestamps are standardized to Beijing time (UTC+8), with client-side relative time display.
    -   **Security**: CSRF protection, unique constraints on identifiers, and secure data handling.

## External Dependencies
-   **PostgreSQL**: Primary relational database.
-   **MongoDB**: NoSQL database for chat messages.
-   **Redis**: Optional caching layer.
-   **阿里云短信服务 (Alibaba Cloud SMS)**: For SMS verification codes (`ALIYUN_ACCESS_KEY_ID`, `ALIYUN_ACCESS_KEY_SECRET`, `ALIYUN_SMS_SIGN_NAME`, `ALIYUN_SMS_TEMPLATE_CODE`).
-   **SMTP (Email Service)**: For password reset emails, supporting SSL/TLS (`SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_SSL`).
-   **WeChat Open Platform OAuth**: For web WeChat login (`WECHAT_APP_ID`, `WECHAT_APP_SECRET`, `WECHAT_REDIRECT_URI`).
-   **WeChat Mini Program**: Requires separate registration and AppID/AppSecret from WeChat Mini Program platform (`WX_MINIPROGRAM_APP_ID`, `WX_MINIPROGRAM_APP_SECRET`).

## Recent Changes (December 2, 2025)

### Chat Message Timestamp and Deduplication Fix
-   **Root Cause**: WebSocket and REST API returned inconsistent message formats - WebSocket lacked `_id` field and used different timestamp formats, causing Set-based deduplication to fail
-   **Backend Fixes**:
    -   `ChatWebSocketHandler.on_message`: Added `_id`, `id`, `timestamp_ms`, `time` fields to pushed messages
    -   `ChatWebSocketHandler.send_stored_messages`: Fixed timezone handling - MongoDB returns UTC naive datetime, now properly converts to UTC+8
    -   `MessageAPIHandler.get`: Added `timestamp_ms` field and fixed timezone processing
    -   `SendMessageAPIHandler.post`: Added complete message format with `timestamp_ms` to WebSocket push
    -   `MiniprogramMessagesHandler`: Added `_id` and `timestamp_ms` fields for consistency
-   **Frontend Fixes (room.js)**:
    -   `addMessage`: Prioritizes `_id` for deduplication, uses `timestamp_ms` for sorting
    -   `pollNewMessages`: Updated to use `_id` and `timestamp_ms` (consistent with addMessage)
    -   `loadChatHistory`: Updated to use `_id` and `timestamp_ms` (consistent with WebSocket)
-   **Web Frontend Fix (chat.js)**: String timestamps "YYYY-MM-DD HH:MM:SS" parsed as UTC+8
-   **Unified Message Format**: All endpoints now return `_id`, `id`, `timestamp` (string), `timestamp_ms` (milliseconds), `time` (HH:MM)
-   **Note**: Legacy data with non-standard timestamp formats may still return `timestamp_ms=0`. Consider running a data migration script for production if issues persist.

## Recent Changes (December 1, 2025)

### Dynamic Tags Feature
-   **New API**: `/api/miniprogram/active_tags` - Returns only tags that are actually used by active products (not preset categories)
-   **Backend Handler**: `MiniprogramActiveTagsHandler` queries distinct product tags from database, filtering for active products with stock > 0
-   **Frontend Integration**:
    -   Added `getActiveTags()` method to `api.js`
    -   Modified `list.js` to call `loadActiveTags()` on page load/show, dynamically updating the categories filter
    -   Product list page now shows only tags that have associated products, improving UX and filter relevance
-   **Example**: If platform only has products tagged "电子产品" and "书籍", only those 2 tags + "全部" are shown (not all 8 preset categories)

### Room Number Constraint Removed
-   **Database Change**: Removed UNIQUE constraint from `room_number` column in `xu_user` table
-   **Model Update**: Modified `models/user.py` to remove `unique=True` from `room_number` field
-   **Allows**: Multiple users can now have the same room number (e.g., family members in same apartment)

### Profile Edit Data Consistency Fix
-   **Issue**: When API update failed, frontend displayed modified values while database remained unchanged ("fake update")
-   **Solution**: Added rollback logic to `saveProfileData()` in `edit.js` - on API failure, all form fields revert to original values from `userInfo`
-   **Result**: Frontend display always matches actual database state

## Recent Changes (November 29, 2025)

### Critical Bug Fixes - Image Loading (Production) - FINAL FIX
-   **Image Handler Issue**: Fixed 500 errors in production mini program image loading
-   **Root Cause**: WeChat Mini Program `<image>` tags interpret relative paths (like `/static/images/xxx`) as local resources, not remote server URLs
-   **Solution**: Created `getImageUrl()` and `getDefaultAvatarUrl()` utility functions in `config.js` to convert filenames to complete absolute URLs (e.g., `https://okashii.top/static/images/{filename}`)
-   **Changes Made**:
    -   Added `getImageUrl()` and `getDefaultAvatarUrl()` functions to `miniprogram/utils/config.js`
    -   Modified `list.js` to process product images with `getImageUrl()`
    -   Modified `detail.js` to use `getImageUrl()` for product images and seller avatars
    -   Modified `chat/list.js` and `chat/room.js` to process avatar URLs
    -   Modified `profile/profile.js` to handle user avatar URLs
    -   Modified `utils/share.js` to use complete URLs for share images
    -   Updated all WXML templates to use processed URLs directly (removed relative path prefixes)
-   **Result**: All product images, user avatars, and share images now load correctly in production environment via complete absolute URLs

### Mini Program Fixes
-   **WebSocket Path**: Fixed duplication issue (`/ws/ws/` -> `/ws/`)
-   **TabBar Display**: Fixed - removed `pages/index/index` from pages array, set `pages/product/list` as entry point (first tabBar page)
-   **TabBar**: 4 tabs: 物品 (list.js), 消息 (chat list), 订单 (order list), 我的 (profile)
-   **Publish Button**: Added "发布商品" text alongside "+" icon with improved styling
-   **Navigation**: Fixed profile page navigation to use `wx.switchTab()` for tabBar pages
-   **Categories**: Synchronized categories across list.js and publish.js (数码产品, 家用电器, 服装鞋包, 图书音像, 运动户外, 美妆个护, 家居用品, 其他)
-   **Image URLs**: All image URLs now use complete absolute paths via `getImageUrl()` function, supporting both dev (`http://localhost:5000`) and production (`https://okashii.top`) environments
-   **Development Mode**: Set `isDev = true` in config.js for proper localhost development URLs (http://localhost:5000)
-   **System Broadcasts**: Added 📢 系统广播 section to chat/room page showing latest 10 product uploads with room number, time, and product name
-   **Chat Room Fixes**: Fixed undefined orderId error, added default avatar image, corrected orderId/productId null handling
-   **Real-time Chat**: Fixed sendMessage parameters to match backend API (`friend_id` and `message` instead of `receiver_id` and `content`)

### Backend Updates
-   **New API**: `/api/miniprogram/messages/mark_read` for marking chat messages as read
-   **Broadcasts API**: `/api/miniprogram/broadcasts` returns latest 10 products with user room number, relative time (x小时前/x天前), and product name
-   **Image Route**: Added `/images/(.*)` static file route mapping to `mystatics/images/`
-   **Default Avatar**: Created `mystatics/images/default-avatar.png` for missing user avatars

### Admin Script
-   Created `scripts/add_admin_prod.py` for production VPS admin account setup
-   Fixed import to use `from base.base import Base, engine`

### Product Ownership Management (November 29, 2025)
-   **Product Detail Page**: Added ownership detection (`isOwner` flag) to show different buttons:
    -   **Own products**: Edit and Delete buttons with "我的商品" tag
    -   **Other's products**: Favorite, Contact Seller, and Buy buttons
-   **My Products Page** (`miniprogram/pages/product/my-list`): New management page with:
    -   Status filtering tabs: 全部/在售/已售
    -   Product list with image, name, price, status, quantity, and upload time
    -   Edit and Delete actions for each product
    -   Empty state with publish button
    -   Pull-to-refresh support
-   **Profile Navigation**: "我的商品" now navigates to dedicated management page instead of product list
-   **Backend API**: `GET /api/miniprogram/my_products?status=all|在售|已售完` returns user's own products