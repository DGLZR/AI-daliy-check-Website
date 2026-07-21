@echo off
echo AI工作日报助手 - 介绍网站
echo ========================
echo.
echo 选择操作:
echo 1. 启动开发服务器
echo 2. 构建Docker镜像
echo 3. 启动Docker容器
echo 4. 停止Docker容器
echo 5. 退出
echo.
set /p choice=请输入选项 (1-5): 

if "%choice%"=="1" (
    echo 启动开发服务器...
    python app.py
) else if "%choice%"=="2" (
    echo 构建Docker镜像...
    docker-compose build
) else if "%choice%"=="3" (
    echo 启动Docker容器...
    docker-compose up -d
) else if "%choice%"=="4" (
    echo 停止Docker容器...
    docker-compose down
) else if "%choice%"=="5" (
    exit
) else (
    echo 无效选项
    pause
)