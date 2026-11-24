# 云声实时语音客服

基于 FastAPI 和火山引擎豆包实时语音 3.0（Seeduplex）的全双工语音客服。浏览器持续上传 16kHz PCM 音频，服务端安全代理到火山 WebSocket，实时返回 24kHz PCM 音频与对话文本。

## 快速开始

1. 创建虚拟环境并安装依赖：

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. 在豆包语音新版控制台开通“端到端实时语音”，创建 API Key，并填写 `.env`：

   ```env
   VOLC_REALTIME_API_KEY=你的豆包语音API_Key
   ```

3. 启动服务：

   ```powershell
   uvicorn app.realtime_app:app --reload
   ```

4. 打开 <http://127.0.0.1:8000>，允许麦克风权限。非本机设备访问时必须配置 HTTPS。

## 接口

- `GET /api/health`：健康检查与配置状态
- `GET /api/config`：公开品牌、模型和接入状态
- `WS /api/realtime/ws`：浏览器与火山实时语音之间的安全代理
- `GET /docs`：FastAPI 接口文档

API Key 只由服务端读取，不会传给浏览器。生产环境仍需补充用户鉴权、限流、HTTPS、隐私告知、工单系统和人工客服转接。
