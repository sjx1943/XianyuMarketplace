# 小区二手商品交易平台

## Overview
This project is a community-based second-hand goods trading platform built with the Tornado framework, designed for deployment on Replit. It aims to facilitate the exchange of idle items among residents, emphasizing ease of use, security, and a rich user experience. Key capabilities include robust user authentication, a real-time chat system, comprehensive product listings with image uploads, and an administrative dashboard. The platform also features a WeChat Mini Program frontend that shares the same backend API, offering a native mobile experience. The project's vision is to create a streamlined and trustworthy environment for local community trading, fostering local engagement and expanding into the e-commerce market.

## User Preferences
I prefer iterative development with clear, concise explanations for each step. Please prioritize core functionality and user experience. I value clean code and robust error handling. For any significant changes or architectural decisions, please ask for my approval first. Ensure all user-facing features are mobile-responsive and accessible. Do not make changes to folder `base/`. Do not make changes to file `config.ini`.

## System Architecture
The platform is built on Python 3.11 with the Tornado 6.4.2 web framework.

### Development and Production Environment Separation
-   **Development (Replit)**: Used for coding, testing, and iteration, leveraging Replit's PostgreSQL and MongoDB.
-   **Production (VPS)**: Utilizes a RackNerd VPS, Containerd + Docker Compose, and self-deployed PostgreSQL + MongoDB for stable online service.

### Core Technology Stack
-   **Backend**: Python 3.11 + Tornado 6.4.2
-   **ORM**: SQLAlchemy 2.0.28
-   **Relational Database**: PostgreSQL 15 (user data, products, orders)
-   **NoSQL Database**: MongoDB 7 (chat messages)
-   **Cache**: Redis 7 (optional)
-   **Container Engine**: Containerd (production)
-   **Web Server**: Nginx (production reverse proxy)
-   **Frontend**: HTML, CSS, JavaScript, WebSockets for web; WeChat Mini Program (WXML, WXSS, JavaScript) for mobile.

### UI/UX Decisions
-   Modern, responsive design with intuitive navigation.
-   Inline error messages, dynamic navigation, and mobile-friendly elements.
-   Responsive chat interface.

### Technical Implementations & Feature Specifications
-   **Authentication**: Supports username/room number + password, phone + SMS, and WeChat OAuth (web and mini program).
-   **Session Management**: Per-handler session pattern to prevent cross-request pollution.
-   **Chat System**: Real-time messaging with unread notifications, search, and a draggable, responsive sidebar. Features long-press delete for messages and unified timestamp handling (UTC+8 Beijing time displayed on frontend).
-   **Product Management**: Comprehensive listing with instant image preview, multi-tag selection, optimized multi-field search, and product condition selection. Includes dynamic tag filtering, allowing only tags with active products to be displayed.
-   **Order Workflow**: Simplified states (`pending`, `shipped`, `completed`), including seller-side unread notifications and a 24-hour automatic confirmation countdown. Only completed transactions allow buyer reviews. Order creation has robust error handling for MongoDB connections.
-   **Admin Dashboard**: Comprehensive interface for user, product, and order management, secured by an `is_admin` flag.
-   **Core Concepts**:
    -   **Room Number Identity**: Users identified by a mandatory "room number" (e.g., '3-1-801'), with support for multiple users having the same room number.
    -   **Time Handling**: All timestamps are standardized to Beijing time (UTC+8), with client-side relative time display. Backend APIs return raw UTC, frontend handles conversion.
    -   **Security**: CSRF protection, unique constraints on identifiers, and secure data handling.
    -   **Image Handling**: All image URLs are converted to complete absolute URLs for correct display across environments (dev/prod, web/mini program).
    -   **Product Ownership**: Product detail pages differentiate between owner's products (edit/delete) and others' products (favorite/contact seller/buy). A dedicated "My Products" page allows users to manage their listings.
    -   **System Broadcasts**: Real-time broadcast of new product uploads in chat rooms.
    -   **Performance Optimization (2024-12)**: Mini program pages optimized to reduce loading lag:
        - 5-second API timeout mechanisms to prevent infinite loading states
        - Smart caching with `lastLoadTime` to avoid redundant API calls within 2 seconds
        - Anti-duplicate loading flags (`isLoading`, `isSilentLoading`) to prevent concurrent requests
        - Loading initial values set to `false` to avoid showing loading state on page open
        - Chat polling interval increased from 10s to 20s to reduce API frequency
        - Parallel loading with `Promise.all` where appropriate
        - Primary image setting only available on product detail page for owners

## External Dependencies
-   **PostgreSQL**: Primary relational database.
-   **MongoDB**: NoSQL database for chat messages.
-   **Redis**: Optional caching layer.
-   **阿里云短信服务 (Alibaba Cloud SMS)**: For SMS verification codes.
-   **SMTP (Email Service)**: For password reset emails.
-   **WeChat Open Platform OAuth**: For web WeChat login.
-   **WeChat Mini Program**: Requires separate registration and AppID/AppSecret for mini program functionality.