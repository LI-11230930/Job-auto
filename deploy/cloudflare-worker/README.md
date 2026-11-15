# Job-auto 零知识加密云端中转（Cloudflare Worker + KV）

本目录包含可直接部署到 Cloudflare Workers 的零知识加密中转服务端代码（[`worker.js`](worker.js)）。

## 安全模型

- **端到端加密（AES-256-GCM）**：密钥由桌面端 `.env` 中的 `CLOUD_RELAY_SECRET`（经 `SHA-256` 派生）本地持有，`pairing_id` 作为 AAD 认证附加数据。
- **零知识中转**：Cloudflare Worker 与 KV 中**仅存放 AES-256-GCM 密文与到期 TTL**，服务端无法解密简历或岗位内容。
- **手机端即时审阅**：访问 Worker 的 `/mobile` 路径（HTTPS 安全上下文），在浏览器内存中使用原生 WebCrypto (`crypto.subtle`) 本地解密审阅并加密回传审批动作。

## 部署 / 更新步骤

1. 在 Cloudflare Dashboard 创建 **Workers & Pages** → 创建一个 KV Namespace（例如 `JOB_AUTO_RELAY_KV`）。
2. 进入你的 Worker → **Settings → Bindings → Add → KV namespace**：
   - **Variable name** 必须填：`RELAY_KV`
   - **KV namespace** 选择上一步创建的 KV。
3. 将本目录 [`worker.js`](worker.js) 的完整内容粘贴覆盖部署到 Worker（或通过 Wrangler 部署）。
4. 在桌面端 `.env` 中设置你的配对口令：
   ```ini
   CLOUD_RELAY_SECRET=你的强随机配对口令
   ```
5. 在桌面 App **设置 → 云端加密审阅与邮件兜底** 中填入 Worker 地址与 `pairing_id`，点击：
   - **立即加密推送到云端**：将待审岗位列表加密推送至 `/push-batch`
   - 手机访问 `https://<你的Worker域名>/mobile?pairing_id=<pairing_id>`，输入口令即可拉取解密并勾选 `通过入队列 / 暂缓 / 不考虑`
   - 回到桌面 App 点击 **拉取手机端审批结果**：自动解密回写本地 SQLite 审批与投递队列。

## API 路由规范

| 路由 | 方法 | 说明 |
| --- | --- | --- |
| `/health` | `GET` | 健康检查与 KV 绑定状态 |
| `/mobile` | `GET` | 手机端零知识 WebCrypto 审阅网页 |
| `/push-batch` | `POST` | 上传加密待审包信封（附带 `ttl_days`） |
| `/pull-batch?pairing_id=...` | `GET` | 手机端拉取最新加密待审包信封 |
| `/ack-actions` | `POST` | 手机端提交加密审批结果信封 |
| `/pull-actions?pairing_id=...` | `GET` | 桌面端读取并清理已同步的加密动作信封 |
