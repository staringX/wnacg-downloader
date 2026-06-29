# MangaVault 前端（React + Vite）

依据 [`docs/フロントエンド再設計実装計画.md`](../docs/フロントエンド再設計実装計画.md) 与
[`docs/design/DESIGN_SPEC.md`](../docs/design/DESIGN_SPEC.md) 重构的 React SPA，
替代旧的 Next.js 前端（已移除）。

## 技术栈

- **React 19 + Vite**（SPA，无路由，标签页用状态管理）
- **Tailwind v4 + CSS 变量令牌**（`src/styles/tokens.css`，UI 以手写为主）
- 自前 `ThemeProvider`（`<html data-theme>` 切换暗/亮色变量）
- `lucide-react` 图标；`@radix-ui/react-dialog` 仅用于设置弹窗
- SSE（`EventSource`）实时同步任务/下载进度

## 开发

```bash
npm install
npm run dev      # http://localhost:5173，/api 与 /api/events(SSE) 代理到后端
```

后端地址默认 `http://localhost:8000`，可用环境变量覆盖：

```bash
VITE_BACKEND_URL=http://192.168.1.10:8000 npm run dev
```

## 构建

```bash
npm run build    # 产物输出到 dist/
```

## 部署（方案B：FastAPI 集约配信）

生产环境不单独运行前端容器。仓库根目录的多阶段 [`Dockerfile`](../Dockerfile)：

1. Node 阶段执行 `npm run build` 生成 `dist/`；
2. 复制 `dist/` 到后端镜像的 `app/static/`；
3. FastAPI 通过 `StaticFiles` + SPA 回退（[`backend/app/main.py`](../backend/app/main.py)）
   在同一进程、同一源下同时提供前端与 `/api`，因此 `API_BASE_URL` 保持为空字符串。

## 目录

```
src/
  components/common/    ThemeProvider · Toast · Switch · AuthorSectionHeader
  components/layout/    Header · SyncProgressStrip · MobileMenu · SyncFab
  features/collection/  收藏夹（StatCards · Toolbar · MangaCard · MangaRow · SelectionBar）
  features/recent-updates/  最近更新（告知バー · RecentUpdateCard）
  features/settings/    SettingsDialog（含「更新下载状态」数据维护）
  hooks/                use-app-data · use-downloads · use-sync · use-task-status(SSE) · use-mobile
  lib/api/              后端 API 客户端（沿用旧前端的契约，不变）
  lib/types/            类型定义
  styles/tokens.css     设计令牌（DESIGN_SPEC §1）
```
