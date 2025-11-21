# 小区二手商品交易平台

## Overview
This project is a community-based second-hand goods trading platform built with the Tornado framework, adapted for deployment on Replit. It facilitates the exchange of idle items among residents, focusing on ease of use, security, and a rich user experience. Key features include robust user authentication (password, phone number + SMS, and WeChat OAuth), a real-time chat system, comprehensive product listings with image uploads, and an administrative dashboard for platform management. The platform includes a **WeChat Mini Program** frontend (`miniprogram/` folder) that provides a native mobile experience sharing the same backend API. The platform aims to create a streamlined and trustworthy environment for local community trading.

## User Preferences
I prefer iterative development with clear, concise explanations for each step. Please prioritize core functionality and user experience. I value clean code and robust error handling. For any significant changes or architectural decisions, please ask for my approval first. Ensure all user-facing features are mobile-responsive and accessible. Do not make changes to folder `base/`. Do not make changes to file `config.ini`.

## System Architecture
The platform is built on Python 3.11 with the Tornado 6.4.2 web framework.
-   **Backend**: Python 3.11 + Tornado 6.4.2.
-   **Database**: PostgreSQL for main data (Replit-provided), MongoDB for chat messages. SQLAlchemy 2.0.28 is used as the ORM.
-   **Frontend**: 
    -   **Web**: HTML, CSS, JavaScript, and WebSockets for dynamic interactions.
    -   **WeChat Mini Program**: Native mini program built with WXML, WXSS, and JavaScript (located in `miniprogram/` folder).
-   **UI/UX**: Modern, responsive design with a focus on intuitive navigation. Features like inline error messages, dynamic navigation bars, mobile-friendly button sizing, and responsive chat layouts enhance usability.
-   **Authentication**: Supports multiple login methods:
    -   Web: username/room number + password, phone number + SMS verification, WeChat OAuth (QR code for PC, in-browser for mobile)
    -   Mini Program: WeChat login via `wx.login()` API with automatic user creation/linking
-   **Session Management**: Employs a per-handler session pattern to prevent cross-request session pollution.
-   **Chat System**: Real-time messaging with unread notifications, message search, and a draggable, responsive sidebar.
-   **Product Management**: Features include product listing with instant image preview, multi-tag selection, and an optimized search function supporting multiple fields.
-   **Order Workflow**: Simplified states: `pending`, `shipped`, `completed`. Includes seller-side unread order notifications.
-   **Admin Dashboard**: A comprehensive administrative interface for user, product, and order management, including statistics and pagination, secured by `is_admin` flag.
-   **Deployment**: Configured for Replit Autoscale with `python app.py --port=5000` as the run command and `/health` for health checks.
-   **Core Concepts**:
    -   **Room Number Identity**: Users are identified by a mandatory "room number" (e.g., '3-1-801') for all transactions and communications.
    -   **Time Handling**: All timestamps are standardized to Beijing time (UTC+8), with client-side relative time display and automatic refresh.
    -   **Security**: CSRF protection for OAuth, unique constraints on identifiers (phone, OpenID), and secure handling of sensitive data.

## External Dependencies
-   **PostgreSQL**: Primary relational database for user data, products, orders.
-   **MongoDB**: NoSQL database specifically used for storing chat messages.
-   **Redis**: Optional caching layer.
-   **阿里云短信服务 (Alibaba Cloud SMS)**: Used for sending SMS verification codes during phone number login and password reset. Requires `ALIYUN_ACCESS_KEY_ID`, `ALIYUN_ACCESS_KEY_SECRET`, `ALIYUN_SMS_SIGN_NAME`, `ALIYUN_SMS_TEMPLATE_CODE`.
-   **SMTP (Email Service)**: Used for password reset emails, supporting SSL/TLS. Configurable via `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_SSL`. Defaults configured for QQ Mail.
-   **WeChat Open Platform OAuth**: Integrated for WeChat login (web version), requiring `WECHAT_APP_ID`, `WECHAT_APP_SECRET`, `WECHAT_REDIRECT_URI`.
-   **WeChat Mini Program**: Requires separate registration and AppID/AppSecret from WeChat Mini Program platform (mp.weixin.qq.com). Environment variables: `WX_MINIPROGRAM_APP_ID`, `WX_MINIPROGRAM_APP_SECRET`.

## Recent Changes (Nov 21, 2025)
-   **WeChat Mini Program Integration**: Added complete WeChat Mini Program frontend with backend API support
    -   Created `miniprogram/` folder structure with pages, components, and utilities
    -   Implemented `/api/miniprogram/login` endpoint for WeChat OAuth (wx.login)
    -   Created API wrapper (`miniprogram/utils/api.js`) for all backend endpoints
    -   Added bcrypt password hashing for auto-created mini program accounts (security compliance)
    -   Created comprehensive deployment guide: `MINIPROGRAM_DEPLOYMENT_GUIDE.md`