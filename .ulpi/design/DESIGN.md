---
project: EasyNovel
register: product
aesthetic_direction: technical / utilitarian
color_strategy: restrained
design_system: Radix UI primitives
visual_density: 6
motion_intensity: 1
---

# Design Read
一间安静的小说编剧室：正文占据视线中心，剧情证据像剪辑台的轨道一样可定位、可检查。

## Signature
章节编辑页右侧的“证据轨道”：每条人物状态、伏笔和审稿意见带章节来源，明确区分已确认、候选与未来计划。侧边导航采用窄竖轨加作品目录，避免通用仪表盘的卡片墙。

## Locked tokens
| Role | Hex | OKLCH approximation | Use |
|---|---|---|---|
| background | #eef2f1 | 0.955 0.005 165 | 工作区底色 |
| surface | #ffffff | 1 0 0 | 正文、表单 |
| rail | #213b39 | 0.33 0.03 185 | 主导航 |
| text | #203431 | 0.31 0.025 165 | 正文与标签 |
| muted | #526760 | 0.49 0.025 165 | 次要文字 |
| border | #c4d1cb | 0.85 0.02 165 | 分隔线 |
| accent | #21685d | 0.47 0.07 175 | 主操作与选中 |
| success | #21685d | 0.47 0.07 175 | 已确认 |
| warning | #835600 | 0.49 0.10 75 | 待审 |
| danger | #a13537 | 0.48 0.14 25 | 错误与冲突 |
| info | #526760 | 0.49 0.025 165 | 提示 |

Contrast: text/white > 12:1, muted/white > 5:1, white/accent > 6:1, white/rail > 11:1. Muted is minimum contrast for small text. Never encode a state by color alone.
Type: Microsoft YaHei UI for controls; Microsoft YaHei for body; Microsoft JhengHei for chapter headings; Consolas for token counts. No external font download. Novel text 18px/1.95, controls 13–14px, heading 24px, titles 32px. Text measure 38 Chinese characters.
Spacing: 0,2,4,8,12,16,20,24,32,40,48,64. Radius: 4/8px. Icons: lucide-react only. Motion: 100ms opacity; reduced motion disables transitions. No gradients, glass, ornamental cards, fake sample data or fabricated metrics.

## Voice and interaction
简体中文，具体动词：保存草稿、确认入库、审核计划、继续生成、分析影响。标题和反馈不使用营销措辞。Every screen must read as the same product if placed side by side.

## Preflight
Identity tokens and a single icon family locked; no banned palette/fonts/layout; state and focus requirements in workstation.md. No inspiration references supplied; derive from authoring task. Spec self-review scores: distinctiveness 3, hierarchy 4, consistency 4, accessibility 3, coverage 4, copy 4, restraint 4, motivated motion 3 (29/32). Implementation must verify contrast and actual keyboard paths.
