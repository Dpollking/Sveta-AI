@echo off
REM Builds dist\SvetaAI.exe — a single-file desktop app (native window, no
REM terminal needed). Run this from a venv that has requirements.txt AND
REM requirements-desktop.txt installed (NOT requirements-rag.txt, unless you
REM want chromadb/sentence-transformers/torch bundled — that adds ~1GB and
REM slows down every cold start; without them the app just uses the keyword
REM RAG fallback, which is fine for most use).

setlocal

if not exist .venv (
  echo Creating virtualenv...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install --quiet -r requirements-desktop.txt

pyinstaller --name SvetaAI --onefile --noconsole ^
  --add-data "frontend;frontend" ^
  --add-data "admin;admin" ^
  --add-data "knowledge;knowledge" ^
  --add-data "media;media" ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan.on ^
  desktop_app.py

echo.
echo Done. dist\SvetaAI.exe is standalone — copy it anywhere, a "data\" folder
echo (database + chroma index) will be created next to it on first run.
endlocal
