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

## Recent Changes (November 29, 2025)

### Mini Program Fixes
-   **WebSocket Path**: Fixed duplication issue (`/ws/ws/` -> `/ws/`)
-   **TabBar Display**: Fixed - removed `pages/index/index` from pages array, set `pages/product/list` as entry point (first tabBar page)
-   **TabBar**: 4 tabs: 物品 (list.js), 消息 (chat list), 订单 (order list), 我的 (profile)
-   **Publish Button**: Added "发布商品" text alongside "+" icon with improved styling
-   **Navigation**: Fixed profile page navigation to use `wx.switchTab()` for tabBar pages
-   **Categories**: Synchronized categories across list.js and publish.js (数码产品, 家用电器, 服装鞋包, 图书音像, 运动户外, 美妆个护, 家居用品, 其他)
-   **Image URLs**: Added `/images/` route for direct image access, frontend now uses `https://okashii.top/images/{filename}`

### Backend Updates
-   **New API**: `/api/miniprogram/messages/mark_read` for marking chat messages as read
-   **Image Route**: Added `/images/(.*)` static file route mapping to `mystatics/images/`

### Admin Script
-   Created `scripts/add_admin_prod.py` for production VPS admin account setup