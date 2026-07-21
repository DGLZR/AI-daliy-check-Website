# AI工作日报助手 - 介绍网站

这是AI工作日报助手的介绍网站，用于展示项目功能和提供下载。

## 功能特性

- 响应式设计，支持移动端访问
- 现代化UI界面
- 文件上传和管理功能
- Docker容器化部署

## 快速开始

### 开发环境

1. 安装Python依赖：
```bash
pip install -r requirements.txt
```

2. 启动开发服务器：
```bash
python app.py
```

3. 访问网站：http://localhost:5000

### Docker部署

1. 构建并启动容器：
```bash
docker-compose up -d
```

2. 访问网站：http://localhost

3. 管理页面：http://localhost/admin

## 文件上传

1. 访问管理页面：http://localhost/admin
2. 上传exe文件（支持.exe, .zip, .rar, .7z格式）
3. 文件会自动保存到uploads目录

## 目录结构

```
├── app.py              # Flask应用主文件
├── requirements.txt    # Python依赖
├── Dockerfile          # Docker配置
├── docker-compose.yml  # Docker Compose配置
├── nginx.conf          # Nginx配置
├── start.bat           # Windows启动脚本
├── static/             # 静态文件目录
│   ├── index.html      # 主页
│   ├── style.css       # 样式文件
│   └── script.js       # JavaScript文件
└── uploads/            # 上传文件目录
```

## 配置说明

- 默认端口：5000（开发）/ 80（Docker）
- 上传文件大小限制：500MB
- 支持的文件类型：exe, zip, rar, 7z

## 访问地址

- 网站首页：http://localhost
- 管理页面：http://localhost/admin
- API接口：
  - GET /api/files - 获取文件列表
  - POST /api/upload - 上传文件
  - GET /api/latest - 获取最新版本