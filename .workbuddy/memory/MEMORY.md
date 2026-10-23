# 奶蛙桌宠项目 - 长期笔记

## 项目概况
- 双子项目：① `app/` Python 桌宠（已上线，奶蛙桌宠.lnk）；② `奶蛙快跑/` 网页跑酷小游戏（2026-10-23 新建）。
- 角色设定：奶蛙 = 黄色胖蛙，素材朝左，向右运动需镜像。

## 用户偏好
- 做新东西前希望被问清楚，确认 99% 把握再动手。
- 手机端选了「网页 App」形态；PC 端要 exe（pywebview 包装网页）。

## 游戏约定（奶蛙快跑）
- 2026-10-23 起为 3D 双列版（three.js 本地化 vendor/）：背后视角纵深跑酷，上滑跳/下滑蹲/左右滑换道；金币吃到即消失+HUD 计数。
- **奶蛙 3D 形象来自用户三视图 image-to-3D 生成的 GLB**（assets/frog-model.js 内嵌 base64），绝不允许用程序化建模或 AI 自创形象替代；模型含背/侧/正三座雕像，按状态切换（奔跑=背面、菜单/死亡=正面）。
- 有主题系统：暖阳草原 / 苔泽雨林 / 铃兰花序 / 蘑菇山谷（THEMES + 菜单 themePick + ?theme= 调试参数 + localStorage nf_theme）。加新主题照 THEMES 结构复制一项（sky/fog/hemi/sun/exposure/road/tint/linear），`linear:true` 的还要 `convertSRGBToLinear()`；**光照总量 ≈1.1**（hemi + sun），否则 r128 + sRGB 输出会整屏发白。
- 打包：`python pc/build_exe.py`（用 envs/game 这个 venv 的 python），--add-data 需含 index.html/assets/vendor 三项。

## 环境
- 系统 Python 3.10（D:/…AppData/Local/Programs/Python/Python310）带 Pillow；managed 3.13 没有。
- 无头截图：普通 HTML 页用 Edge 命令行 `--headless=new --screenshot` 正常；但**游戏页会全黑**，必须走 CDP（`--remote-debugging-port=9222` + node22 内置 WebSocket + `Page.captureScreenshot`）。
