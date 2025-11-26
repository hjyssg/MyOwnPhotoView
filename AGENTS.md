# AGENTS.md

## Project Overview

This is the **Local Smart Gallery**, a web application designed to scan, organize, and display a unified timeline of local photo and video files. The goal is to create a seamless browsing experience for media collections.

## Tech Stack

-   **Backend**: Python with **FastAPI**.
    -   **Database**: SQLite with **SQLAlchemy**.
    -   **Video Processing**: **OpenCV** (`cv2`) for thumbnail generation and metadata extraction.
    -   **Server**: **Uvicorn**.
-   **Frontend**: JavaScript with **React**.
    -   **API Client**: **axios**.
    -   **Build Tool**: Create React App.

## Project Structure

```
.
├── backend/
│   ├── venv/             # Python Virtual Environment
│   ├── cache/
│   │   └── thumbnails/   # Generated video thumbnails
│   ├── database.py       # SQLAlchemy models and DB setup
│   ├── main.py           # FastAPI application, API endpoints
│   └── scanner.py        # Core logic for scanning media files
├── frontend/
│   ├── public/
│   └── src/
│       ├── App.js        # Main gallery component
│       ├── Lightbox.js   # Modal for viewing single media items
│       ├── App.css
│       └── ...
└── media/                # Default directory for user's media files
```

## How to Run Development Servers

**Important**: The backend and frontend servers must be running concurrently.

1.  **Start Backend Server**:
    -   Ensure you are in the repository root.
    -   The Python virtual environment is located at `backend/venv`.
    -   Run the following command:
        ```bash
        source backend/venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000
        ```

2.  **Start Frontend Server**:
    -   Ensure you are in the repository root.
    -   Run the following command:
        ```bash
        cd frontend && npm start
        ```
    -   The frontend will be available at `http://localhost:3000` and will proxy API requests to the backend at `http://localhost:8000`.

## Key Logic Points

-   **Scanner**: The `backend/scanner.py` script is the core of the media processing. It iterates through a target directory, identifies images and videos, extracts metadata (`creation_time`, `duration`), and generates thumbnails for videos using OpenCV. All metadata is stored in the SQLite database.
-   **Video Streaming**: The `/api/media/stream/{item_id}` endpoint supports HTTP Range Requests (`206 Partial Content`) to ensure large video files can be streamed efficiently without being fully downloaded first. This is crucial for performance.
-   **Thumbnails**: Video thumbnails are **not** generated on-the-fly. They are created once during the initial scan and stored in `backend/cache/thumbnails/`. The frontend loads these static thumbnail images for the grid view.