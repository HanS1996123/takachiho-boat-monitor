FROM python:3.10-slim

# 安裝系統基本元件
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝 Python 依賴套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安裝 Playwright Chromium 瀏覽器與 Linux 系統依賴
RUN playwright install chromium --with-deps

# 複製程式碼進容器
COPY . .

# 啟動監控程式
CMD ["python", "monitor.py"]
