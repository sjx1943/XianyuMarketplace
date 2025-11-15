## 交互习惯
1.默认用中文回复


# xianyu二手平台开发部署文档

## 项目概述
基于 Tornado 框架开发的二手闲置物品交易平台，支持商品发布、实时聊天、订单管理、商品评价、支持商品多图上传等核心功能。采用 Python 3.11 + MySQL + MongoDB + Redis 技术栈，支持 Docker 容器化部署和微信小程序多端适配。

## 环境配置
1. Github的项目地址 (SSH): `git@github.com:sjx1943/mytornado.git`
2. **首次配置**: 请确保你已经 [生成了SSH密钥](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) 并将其 [添加到了你的GitHub账户](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)。SSH方式更安全且无需每次输入密码。

### 基础环境要求
- Python 3.11+
- MySQL 8.0+
- MongoDB 6.0+
- Redis 7.0+
- Docker & Docker Compose（推荐）
- Nginx（生产环境）

### 开发环境搭建

#### 方式一：Docker 一键部署（推荐）
```bash
# 克隆项目 (使用SSH)
git clone git@github.com:sjx1943/mytornado.git
cd mytornado/xianyu/agent_mvc

# 注意：为避免端口冲突，默认端口已调整。
# Nginx: 8088, 8444 | MongoDB: 27019 | Redis: 6381
# 如仍有冲突，请自行修改 docker-compose.yml 文件。

# 启动服务
docker compose up -d --build
```
**网络问题提示**: 如果Docker构建过程中出现网络错误（如无法解析域名），请在 `Dockerfile` 中将 `apt-get` 的软件源更换为国内镜像源（如 `mirrors.aliyun.com`）。

#### 方式二：本地手动部署
# 创建虚拟环境并激活
python3.11 -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置数据库
# 修改 config.ini 中的数据库连接信息

# 启动服务
python app.py --port=8000


## 编程规范

### 后端开发规范

# 导入约定（示例）
import tornado.web
from tornado.ioloop import IOLoop
from models.user import UserModel  # 模型导入路径
from controllers.base import BaseHandler  # 控制器基类

# 类与函数命名
class ProductHandler(BaseHandler):  # 控制器类使用PascalCase
    async def get_product_detail(self, product_id: int) -> dict:  # 函数使用camelCase，添加类型提示
        """获取商品详情
        Args:
            product_id: 商品ID
        Returns:
            商品详情字典
        """
        try:
            # 业务逻辑代码
            return await ProductModel.get_by_id(product_id)
        except Exception as e:
            self.log_error(f"获取商品失败: {str(e)}")  # 统一错误日志
            raise

### 前端开发规范
- HTML模板使用 templates/ 目录，遵循 Tornado 模板语法
- CSS/JS 存放于 mystatics/，使用模块化开发
- 微信小程序页面存放于 miniprogram/pages/，遵循小程序开发规范
- UI optimization strategy is to use a responsive, multi-column grid layout with card-based design. Each card should have uniformly sized images (using `object-fit: cover`), clear status indicators, and distinct sections for information and actions to ensure a clean, consistent, and user-friendly interface.

## 项目结构

项目目录/
├── .venv/                # 虚拟环境（不提交git）
├── .env                  # 环境变量（不提交git）
├── config.ini            # 项目配置文件
├── requirements.txt      # Python依赖 (包含cryptography, beautifulsoup4)
├── Dockerfile            # Docker配置
├── docker-compose.yml    # Docker Compose配置
├── nginx.conf            # Nginx反向代理配置
├── app.py                # 应用入口
├── models/               # 数据模型
│   ├── user.py           # 用户模型
│   ├── product.py        # 商品及商品图片模型
│   └── order.py          # 订单模型
├── controllers/          # 业务控制器
│   ├── product_controller.py  # 商品相关接口
│   ├── chat_controller.py     # 聊天功能接口
│   └── order_controller.py    # 订单处理接口
├── templates/            # HTML模板
├── mystatics/            # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
├── miniprogram/          # 微信小程序代码
└── utils/                # 工具函数
    ├── db.py             # 数据库连接工具
    └── validator.py      # 参数验证工具



## 环境变量设置

# .env 文件
# .env 文件配置示例
MYSQ_HOST=localhost
MYSQ_PORT=3306
MYSQ_USER=root
MYSQ_PASSWORD=your_secure_password
MYSQ_DB=xianyu_db

MONGODB_URI=mongodb://localhost:27017/chat_db
REDIS_URL=redis://localhost:6379/0


DEBUG=False
LOG_LEVEL=INFO


## 开发要点

### 团队模式
- **RoundRobinGroupChat**: 轮询组聊天
- 支持多智能体协作

### 最佳实践
- 先单独测试智能体，再组合成团队
- 使用async/await处理所有操作
- 正确关闭模型客户端连接
- **优先使用环境变量**管理敏感信息，支持容器化部署。
- 虚拟环境不提交到版本控制

#### 前端开发最佳实践
- **JavaScript模块作用域**: 当使用 `<script type="module">` 加载脚本时，其内部定义的函数和变量会存在于独立的模块作用域中，而非全局`window`对象。这会导致在HTML中通过内联事件处理器（如 `onclick="..."`）直接调用这些函数时，出现 `ReferenceError: function is not defined` 的错误。
- **事件处理推荐方案**: 为避免上述作用域问题，推荐在JavaScript脚本内部使用 `element.addEventListener('click', functionName)` 的方式来绑定事件。这种方法将事件监听器直接附加到DOM元素上，无需将处理函数暴露到全局作用域，是更现代且健壮的事件处理方式。


### 数据完整性
- **订单与商品解耦**: 为确保核心交易记录的永久性，订单（`orders`）与商品（`products`）采用“快照 + 软关联”模式。
  - **快照**: 创建订单时，必须将当时的商品核心信息（如 `product_name`）作为独立字段复制到 `orders` 表中。
  - **软关联**: `orders` 表中的 `product_id` 字段必须允许为 `NULL`。当管理员需要物理删除商品时，应先将所有关联订单的 `product_id` 更新为 `NULL`，再删除商品本身。
  - **查询**: 查询订单时，应使用 `OUTER JOIN` 关联商品表，以确保即使商品已被删除，订单记录依然能被检索和展示。

## 文档和资源获取

### MCP服务器配置
始终使用 **context7 MCP server** 搜索指定框架最新文档和代码规范：
- 优先查询官方文档
- 获取最新的API参考和最佳实践
- 查找代码示例和模式
- 验证版本兼容性和新特性

## 注意事项
-所有用户输入必须通过 utils.validator 验证
-密码存储使用 bcrypt 加密，禁止明文存储
-生产环境必须启用 HTTPS，配置在 nginx.conf 中
-定期备份数据库：utils/backup_db.py
- 优化时要有代码审核机制，避免引入新的问题或老问题重复出现

## 性能优化
图片使用 CDN 加速，配置 mystatics/images/ 目录权限
微信小程序使用分包加载：miniprogram/app.json 中配置

## AI代码审查流程
项目已配置专属的AI代码审查命令 `cr`,该命令为特殊设置的"aliases"别名工具，具体配置见.gemini/settings.json
- **AI角色**: 资深Python开发者，精通Tornado、WebSocket及数据库优化。
- **审查范围**: 所有通过 `git add` 暂存的代码。
- **执行时机**: 在执行 `git commit` 前，请务必运行 cr 命令。
- **目的**: 确保代码质量、性能和安全性，统一团队代码风格。

## 自动化功能测试计划

### 1. 测试目标
- **功能验证**: 确保所有核心功能在小程序环境中按预期工作。
- **数据一致性**: 验证小程序端与后端数据库（MySQL + MongoDB）的数据同步准确无误。
- **用户体验**: 保证接口响应迅速，UI布局在不同设备上表现一致。
- **发布准备**: 确保应用质量达到上线标准，解决所有P0和P1级别的缺陷。

### 2. 测试范围
本次测试将覆盖小程序的所有核心业务流程，包括但不限于：
- 用户认证模块
- 商品管理模块
- 订单交易模块
- 实时聊天模块
- 评论与好友模块
- 搜索与浏览模块
- 游客模式权限

### 3. 测试策略与工具

1.  **后端API测试 (集成测试)**
    - **工具**: `pytest` + `requests` + `beautifulsoup4`
    - **策略**: 针对所有对外暴露的API接口编写测试用例，覆盖正常的业务场景、异常参数和边界条件。重点测试涉及多服务（MySQL, MongoDB, Redis）交互的接口。

2.  **小程序端E2E测试 (端到端测试)**
    - **工具**: 微信开发者工具 - 小程序自动化
    - **策略**: 模拟真实用户操作，编写自动化脚本执行完整的业务流程。例如：`用户注册 -> 登录 -> 发布商品 -> 另一用户浏览 -> 购买 -> 双方聊天 -> 确认收货 -> 完成订单`。

### 4. 详细测试用例（部分核心）

| 模块 | 测试点 | 预期结果 | 优先级 |
| :--- | :--- | :--- | :--- |
| **用户认证** | 1. 微信授权登录 | 成功获取用户信息并创建/登录账户 | P0 |
| | 2. 手机号注册/登录 | 注册成功，可以正常登录和退出 | P0 |
| | 3. 密码找回流程 | 用户能通过已验证方式重设密码 | P1 |
| | 4. Session/Token 有效性 | Token过期后，用户被引导至登录页 | P1 |
| **商品管理** | 1. 发布商品（含多图） | 商品信息、图片保存正确，状态为“在售” | P0 |
| | 2. 编辑商品信息 | 修改后的信息能正确显示 | P1 |
| | 3. 商品上下架/删除 | 商品状态变更后，在列表中不可见/可见 | P1 |
| | 4. 商品数量为0自动下架 | 订单完成后，若商品售罄，自动下架 | P1 |
| **订单交易** | 1. 创建订单 | 买家可以成功创建订单，状态为“待处理” | P0 |
| | 2. 卖家处理订单 | 卖家可以更新订单状态（如：已发货） | P0 |
| | 3. 买家确认收货 | 订单状态更新为“已完成”，商品数量减少 | P0 |
| | 4. 取消订单 | 在特定状态下，用户可以取消订单 | P1 |
| **实时聊天** | 1. 发送/接收实时消息 | 消息在聊天窗口中实时显示 | P0 |
| | 2. 查看历史消息 | 重新进入聊天室能加载历史消息 | P1 |
| | 3. 删除好友后发送消息 | 对方好友列表恢复，但聊天记录为空 | P2 |
| **游客模式** | 1. 浏览商品/活动 | 可以正常查看，无权限错误 | P1 |
| | 2. 触发需登录操作 | 点击购买/评论/聊天时，提示登录 | P1 |

### 5. 测试执行与持续集成
- **环境**: 通过 `docker-compose.test.yml` 启动一个独立的、容器化的测试环境。
- **执行**:
  ```bash
  # 确保本地虚拟环境已安装 pytest, requests, beautifulsoup4
  pip install pytest requests beautifulsoup4

  # 运行完整的测试流程
  docker compose -f docker-compose.yml -f docker-compose.test.yml up -d --build && \
  sleep 15 && \
  pytest tests/test_api.py && \
  docker compose -f docker-compose.yml -f docker-compose.test.yml down
  ```
- **CI/CD**: 建议将API测试集成到GitHub Actions等CI/CD流程中，确保代码质量。