# 微信小程序 — ShopAide 跨端复用

## 架构

```
小程序页面 → <web-view src="https://公网地址"/>
                    ↓
            Chainlit Web UI（复用现有 app.py）
                    ↓
            Agent (12 tools) → SQLite + ChromaDB
```

## 使用方式

1. 用微信开发者工具打开此 `miniprogram/` 目录
2. 将 `pages/index/index.wxml` 中的 `YOUR_TUNNEL.trycloudflare.com` 替换为你的 cloudflared 公网地址
3. 在微信公众平台 → 开发管理 → 业务域名中配置该公网地址
4. 点击"预览"→ 手机扫码 → 在小程序中打开 Chainlit 聊天界面

## 面试要点

- 零后端代码改动：WebView 内嵌 Chainlit，Agent 核心完全不变
- 流式输出、多轮记忆、工具调用侧边栏全部保留
- 如需原生微信能力（登录/支付/位置），可扩展原生页面 + `/api/chat` 端点
