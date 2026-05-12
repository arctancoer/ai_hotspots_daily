# AI 热点日报定时任务

推荐使用 GitHub Actions 跑定时任务，避免公司内网只能访问部分网站导致抓取不完整。

## 运行方式

- 自动运行：每天北京时间 09:00。
- 手动运行：进入 GitHub 仓库的 `Actions` 页面，选择 `Daily AI Hotspots`，点击 `Run workflow`。
- 输出位置：`ai_hotspots_reports/latest.md` 和当天日期报告。
- 备份下载：每次 workflow 都会上传 `ai-hotspots-report` artifact。

## Webhook 推送

如果希望生成后自动推送到 Mattermost、飞书兼容 webhook 或其他服务，在 GitHub 仓库里配置这些 Secrets：

- `AI_HOTSPOTS_WEBHOOK_URL`：必填，webhook 地址。
- `AI_HOTSPOTS_WEBHOOK_CHANNEL`：可选，Mattermost channel。
- `AI_HOTSPOTS_WEBHOOK_USERNAME`：可选，机器人名称。

路径：`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`。

## 本地调试

本地仍然可以手动运行，但如果网络受限，部分信源可能抓取失败。

```bash
./run_ai_hotspots_daily.sh --no-webhook
```

安装本地定时任务：

```bash
./install_ai_hotspots_schedule.sh
```
