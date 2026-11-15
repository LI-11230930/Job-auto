"""Built-in open presets for user-selectable LLM and Email SMTP providers."""

from __future__ import annotations

from typing import Any

LLM_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "gemini_interactions": {
        "id": "gemini_interactions",
        "label": "Google Gemini（官方 Key）",
        "mode": "gemini",
        "base_url": "",
        "default_model": "gemini-3.5-flash-lite",
        "reasoning_model": "gemini-2.5-flash",
        "api_key_env": "GEMINI_API_KEY",
        "requires_key": True,
        "hint": "在 Google AI Studio 申请免费/付费 API Key",
    },
    "deepseek": {
        "id": "deepseek",
        "label": "DeepSeek（深度求索）",
        "mode": "openai_compat",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "reasoning_model": "deepseek-reasoner",
        "api_key_env": "DEEPSEEK_API_KEY",
        "requires_key": True,
        "hint": "兼容 OpenAI 接口，性价比极高，适合中文简历与岗位分析",
    },
    "openai": {
        "id": "openai",
        "label": "OpenAI（ChatGPT / GPT-4o）",
        "mode": "openai_compat",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "reasoning_model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "requires_key": True,
        "hint": "使用官方 OpenAI Key 或兼容网关",
    },
    "qwen": {
        "id": "qwen",
        "label": "阿里通义千问（DashScope 百炼）",
        "mode": "openai_compat",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "reasoning_model": "qwen-max",
        "api_key_env": "DASHSCOPE_API_KEY",
        "requires_key": True,
        "hint": "国内直连稳定，使用阿里云百炼 DashScope API Key",
    },
    "kimi": {
        "id": "kimi",
        "label": "Kimi（Moonshot 月之暗面）",
        "mode": "openai_compat",
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "reasoning_model": "moonshot-v1-32k",
        "api_key_env": "MOONSHOT_API_KEY",
        "requires_key": True,
        "hint": "国内直连，长文本理解能力强",
    },
    "zhipu": {
        "id": "zhipu",
        "label": "智谱 GLM（BigModel）",
        "mode": "openai_compat",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
        "reasoning_model": "glm-4-plus",
        "api_key_env": "ZHIPU_API_KEY",
        "requires_key": True,
        "hint": "支持免费额度的 glm-4-flash 模型",
    },
    "siliconflow": {
        "id": "siliconflow",
        "label": "硅基流动（SiliconFlow）",
        "mode": "openai_compat",
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "Qwen/Qwen2.5-72B-Instruct",
        "reasoning_model": "deepseek-ai/DeepSeek-V3",
        "api_key_env": "SILICONFLOW_API_KEY",
        "requires_key": True,
        "hint": "聚合多款开源大模型，注册即有体验额度",
    },
    "ollama": {
        "id": "ollama",
        "label": "本地 Ollama（完全离线免 Key）",
        "mode": "openai_compat",
        "base_url": "http://127.0.0.1:11434/v1",
        "default_model": "qwen2.5:7b",
        "reasoning_model": "qwen2.5:14b",
        "api_key_env": "OLLAMA_API_KEY",
        "requires_key": False,
        "hint": "数据完全不出本机，需提前启动 Ollama 服务",
    },
    "openai_compat": {
        "id": "openai_compat",
        "label": "自定义 OpenAI 兼容接口 / 中转站",
        "mode": "openai_compat",
        "base_url": "",
        "default_model": "",
        "reasoning_model": "",
        "api_key_env": "LLM_API_KEY",
        "requires_key": True,
        "hint": "任意支持 /v1/chat/completions 的服务商（OneAPI / NewAPI 等）",
    },
}


EMAIL_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "qq": {
        "id": "qq",
        "label": "QQ 邮箱",
        "host": "smtp.qq.com",
        "port": 465,
        "security": "ssl",
        "hint": "在 QQ 邮箱网页版【设置 -> 账户 -> 开启 POP3/SMTP 服务】获取 16 位授权码",
    },
    "163": {
        "id": "163",
        "label": "网易 163 邮箱",
        "host": "smtp.163.com",
        "port": 465,
        "security": "ssl",
        "hint": "在 163 邮箱【设置 -> POP3/SMTP/IMAP】开启服务并使用客户端授权密码",
    },
    "126": {
        "id": "126",
        "label": "网易 126 邮箱",
        "host": "smtp.126.com",
        "port": 465,
        "security": "ssl",
        "hint": "在 126 邮箱开启 SMTP 后使用客户端授权密码",
    },
    "gmail": {
        "id": "gmail",
        "label": "Gmail",
        "host": "smtp.gmail.com",
        "port": 587,
        "security": "starttls",
        "hint": "需开启 Google 两步验证并创建 16 位「应用专用密码」(App Password)",
    },
    "outlook": {
        "id": "outlook",
        "label": "Outlook / Hotmail",
        "host": "smtp-mail.outlook.com",
        "port": 587,
        "security": "starttls",
        "hint": "使用微软账户邮箱与对应应用密码",
    },
    "exmail_qq": {
        "id": "exmail_qq",
        "label": "腾讯企业邮箱",
        "host": "smtp.exmail.qq.com",
        "port": 465,
        "security": "ssl",
        "hint": "企业邮箱登录密码或专用客户端密码",
    },
    "aliyun_ent": {
        "id": "aliyun_ent",
        "label": "阿里企业邮箱",
        "host": "smtp.qiye.aliyun.com",
        "port": 465,
        "security": "ssl",
        "hint": "使用阿里企业邮箱账号与安全密码",
    },
    "custom": {
        "id": "custom",
        "label": "自定义 SMTP 服务器",
        "host": "",
        "port": 465,
        "security": "auto",
        "hint": "任意学校邮箱、公司内网邮局或自建 SMTP（465 默认 SSL，587 默认 STARTTLS）",
    },
}


PUSH_PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "none": {
        "id": "none",
        "label": "仅使用 App 内消息中心与桌面弹窗（默认，免配置）",
        "placeholder": "",
        "hint": "本地桌面 App 自动弹出系统提示，无需邮箱或第三方推送服务；后续上架手机端可直接接入系统推送。",
    },
    "bark": {
        "id": "bark",
        "label": "Bark（iPhone / iPad 即时推送）",
        "placeholder": "https://api.day.app/你的BarkKey",
        "hint": "在 iPhone 安装 Bark App 后复制专属推送链接，即可无需邮箱实时接收手机弹窗。",
    },
    "ntfy": {
        "id": "ntfy",
        "label": "ntfy（Android / iOS 开源跨平台推送）",
        "placeholder": "https://ntfy.sh/你的私密Topic名",
        "hint": "手机端安装 ntfy App 订阅同一个 Topic 名即可接收即时提醒。",
    },
    "serverchan": {
        "id": "serverchan",
        "label": "Server酱（微信手机提醒）",
        "placeholder": "https://sctapi.ftqq.com/你的SendKey.send",
        "hint": "绑定微信后直接推送到微信聊天列表，适合国内手机免装 App 提醒。",
    },
    "pushplus": {
        "id": "pushplus",
        "label": "PushPlus（微信 / 手机消息推送）",
        "placeholder": "http://www.pushplus.plus/send/你的Token",
        "hint": "填入 PushPlus Token URL，自动将求职简报与面试提醒推至手机。",
    },
    "custom_webhook": {
        "id": "custom_webhook",
        "label": "自定义手机 / 飞书 / 钉钉 / 企业微信 Webhook",
        "placeholder": "https://your-push-endpoint.example.com/webhook",
        "hint": "发送通用 JSON POST（包含 title / body / text / content 字段）。",
    },
}


def resolve_llm_preset(provider_id: str | None) -> dict[str, Any]:
    key = (provider_id or "gemini_interactions").strip().lower()
    if key == "gemini":
        key = "gemini_interactions"
    if key == "custom":
        key = "openai_compat"
    return LLM_PROVIDER_PRESETS.get(key, LLM_PROVIDER_PRESETS["openai_compat"])


def resolve_email_preset(preset_id: str | None) -> dict[str, Any]:
    key = (preset_id or "qq").strip().lower()
    return EMAIL_PROVIDER_PRESETS.get(key, EMAIL_PROVIDER_PRESETS["custom"])


def resolve_push_preset(preset_id: str | None) -> dict[str, Any]:
    key = (preset_id or "none").strip().lower()
    return PUSH_PROVIDER_PRESETS.get(key, PUSH_PROVIDER_PRESETS["none"])
