# 小区二手商品交易平台

## Overview
This project is a community-based second-hand goods trading platform, facilitating the exchange of idle items among residents. It offers robust user authentication, real-time chat, comprehensive product listings with image uploads, and an administrative dashboard. The platform supports both a web frontend and a WeChat Mini Program frontend. The vision is to create a streamlined, trustworthy, and engaging local community trading environment with potential for e-commerce expansion.

## User Preferences
I prefer iterative development with clear, concise explanations for each step. Please prioritize core functionality and user experience. I value clean code and robust error handling. For any significant changes or architectural decisions, please ask for my approval first. Ensure all user-facing features are mobile-responsive and accessible. Do not make changes to folder `base/`. Do not make changes to file `config.ini`.

## System Architecture
The platform is built on Python 3.11 with the Tornado 6.4.2 web framework, serving both a web frontend and a WeChat Mini Program.

### Core Technology Stack
-   **Backend**: Python 3.11 + Tornado 6.4.2
-   **ORM**: SQLAlchemy 2.0.28
-   **Relational Database**: PostgreSQL 15
-   **NoSQL Database**: MongoDB 7
-   **Cache**: Redis 7 (optional)
-   **Frontend**: HTML, CSS, JavaScript, WebSockets for web; WeChat Mini Program (WXML, WXSS, JavaScript) for mobile.
-   **Security**: WeChat Security 2.0 API (msgSecCheck) + Tencent Cloud IMS

### UI/UX Decisions
-   Modern, responsive design with intuitive navigation, inline error messages, and dynamic elements.
-   A responsive chat interface.
-   WeChat Mini Program frontend includes a "de-e-commerce" version with vocabulary and UI adjustments for compliance.
-   Content security integrated seamlessly with immediate feedback to users.

### Technical Implementations & Feature Specifications
-   **Authentication**: Supports username/room number + password, phone + SMS, and WeChat OAuth.
-   **Chat System**: Real-time messaging with unread notifications.
-   **Product Management**: Comprehensive listings with image uploads (automated thumbnail/medium generation), multi-tag selection, and optimized search. Includes blacklisting. "Set as main image" functionality is available for product editing.
-   **Order Workflow**: Simplified states (`pending`, `shipped`, `completed`) with seller notifications. Includes automatic confirmation of receipt functionality via frontend countdown and backend scheduled tasks.
-   **Admin Dashboard**: Manages users, products, and orders, including user deletion functionality.
-   **Core Concepts**: Room Number Identity, standardized Beijing time (UTC+8), CSRF protection, absolute image URLs, system broadcasts, and performance optimizations.
-   **Storage**: Supports local and cloud object storage (WeChat Cloud Hosting), with WeChat Cloud Hosting prioritized for Mini Program compatibility, and a fallback to local storage for avatar uploads if cloud hosting fails.
-   **Database**: `autoincrement=True` for ID columns and sequence management via migration scripts. N+1 query issues have been addressed in comments and product listings via `joinedload()`.
-   **WeChat Mini Program Integration**: Automatic environment detection for API calls, `cloud://` URL handling, and subscription message integration for order status, new messages, and product sold notifications. Subscription message service includes token expiration auto-retry and comprehensive error handling. Displayed times in the Mini Program are converted from UTC to Beijing Time (UTC+8).
-   **Content Security**: Comprehensive text and image moderation with WeChat msgSecCheck (Security 2.0) and Tencent Cloud IMS. Includes pre-upload validation using Base64 encoding, immediate rejection of non-compliant content, and user-friendly error messages. A local sensitive keyword library is also used.

## External Dependencies
-   **PostgreSQL**: Primary relational database.
-   **MongoDB**: NoSQL database for chat messages.
-   **Redis**: Optional caching layer.
-   **阿里云短信服务 (Alibaba Cloud SMS)**: For SMS verification.
-   **SMTP (Email Service)**: For password reset emails.
-   **WeChat Open Platform OAuth**: For web WeChat login.
-   **WeChat Mini Program Platform**: Requires AppID/AppSecret for mini program functionality and API interactions.
-   **WeChat Cloud Hosting**: Primary object storage for images, especially for WeChat Mini Program assets.
-   **Tencent Cloud IMS**: Image moderation service.