# Local Smart Gallery (支持视频版)

## 📖 项目简介 (Project Overview)

Local Smart Gallery 是一个本地智能媒体库，旨在为您混乱的本地照片和视频文件夹带来秩序。它会自动扫描指定目录下的媒体文件，提取元数据，并将它们统一按时间顺序呈现在一个美观、高效的网页界面中。

无论是您用相机拍摄的照片，还是手机录制的视频，此应用都会将它们无缝地融合在同一个时间轴上，重现您在特定事件（如漫展、旅行）中的完整回忆。

## ✨ 核心功能 (Features)

-   **统一时间线**: 将照片 (`.jpg`, `.png`, `.heic`) 和视频 (`.mp4`, `.mov`, `.avi`) 混合排序在同一个视图中。
-   **视频支持**:
    -   **自动生成缩略图**: 后端在扫描时使用 OpenCV 截取视频第一帧作为预览，避免前端加载大文件。
    -   **流式播放 (Streaming)**: 支持 HTTP Range Requests，即使是几百兆的大视频也能流畅拖动进度条，无需等待完整下载。
    -   **元数据提取**: 自动读取视频的创建时间和时长。
-   **高效浏览**:
    -   **网格视图**: 瀑布流式展示所有媒体，视频文件会以 ▶️ 图标和时长角标进行区分。
    -   **详情视图 (Lightbox)**: 点击任意文件可进入大图/播放器模式，支持键盘左右键切换上一个/下一个。
-   **简单的扫描机制**: 通过一个 API 请求即可启动对媒体文件夹的扫描和索引。

## 🛠️ 技术栈 (Tech Stack)

-   **后端 (Backend)**:
    -   **框架**: Python & **FastAPI**
    -   **数据库**: SQLite & **SQLAlchemy**
    -   **视频处理**: **OpenCV** (`cv2`)
    -   **Web 服务器**: **Uvicorn**
-   **前端 (Frontend)**:
    -   **框架**: **React** (via Create React App)
    -   **HTTP 请求**: **axios**
    -   **视频播放**: 原生 HTML5 `<video>` 标签

## 🚀 快速开始 (Getting Started)

### 先决条件 (Prerequisites)

-   [Python](https://www.python.org/downloads/) (3.8 或更高版本)
-   [Node.js](https://nodejs.org/) 和 [npm](https://www.npmjs.com/) (16.x 或更高版本)
-   (可选) [Git](https://git-scm.com/)

### 本地安装与运行 (Installation & Running Locally)

1.  **克隆仓库 (Clone the repository)**:
    ```bash
    git clone <your-repository-url>
    cd local-smart-gallery
    ```

2.  **设置后端 (Setup Backend)**:
    ```bash
    # 1. 创建并激活 Python 虚拟环境
    python3 -m venv backend/venv
    source backend/venv/bin/activate

    # 2. 安装后端依赖
    pip install -r requirements.txt
    # (注意: 如果没有 requirements.txt, 请根据 AGENTS.md 手动安装)
    # pip install fastapi "uvicorn[standard]" sqlalchemy aiosqlite opencv-python
    ```

3.  **设置前端 (Setup Frontend)**:
    ```bash
    # 1. 进入前端目录并安装依赖
    cd frontend
    npm install
    cd ..
    ```

4.  **放置您的媒体文件 (Place your media files)**:
    -   在项目根目录下有一个 `media/` 文件夹。
    -   将您想要展示的照片和视频文件复制到这里。

5.  **启动应用 (Run the Application)**:

    -   **启动后端服务器**:
        *打开一个终端窗口*
        ```bash
        source backend/venv/bin/activate
        or source backend/venv/Scripts/activate
        uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

       
        ```
        服务器将在 `http://localhost:8000` 运行。

    -   **启动前端开发服务器**:
        *打开一个新的终端窗口*
        ```bash
        cd frontend
        npm start
        ```
        应用将在 `http://localhost:3000` 自动打开。

6.  **开始使用 (Start Using)**:
    -   打开浏览器，访问 `http://localhost:3000`。
    -   点击页面顶部的 **"Scan Media"** 按钮，后端将开始索引您放在 `media/` 文件夹中的所有文件。
    -   扫描完成后，您的照片和视频画廊将呈现在页面上。享受吧！
