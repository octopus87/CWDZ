# 打包说明

生成 **macOS** 与 **Windows** 可双击运行的桌面程序（无需安装 Python）。

## macOS（在本机执行）

```bash
chmod +x build/build.sh
./build/build.sh
```

产物：

| 路径 | 说明 |
|------|------|
| `dist/财务对账工具.app` | 双击启动（推荐） |
| `dist/CWDZ/CWDZ` | 命令行/目录版入口 |

可将 `财务对账工具.app` 拖到「应用程序」文件夹。

## Windows（须在 Windows 电脑上执行）

```bat
build\build.bat
```

产物：`dist\CWDZ\CWDZ.exe` — 请将整个 **`dist\CWDZ` 文件夹** 一起拷贝分发（内含浏览器与配置）。

## 配置

- 默认配置：`config/settings.yaml`（已打入安装包）
- 本地覆盖：在程序目录下 `config/local.yaml`（可复制 `local.yaml.example` 后修改账号、路径）
- 登录状态与下载文件：程序目录下 `data/`（首次运行自动创建）

## 体积说明

安装包约 **300MB+**（含 Chromium 浏览器运行时），属正常现象。

## Windows 压缩包

在 Windows 打包完成后执行：

```bat
build\package_release.bat
```

生成 `dist\CWDZ-Windows-x64.zip`（解压后顶层为 `CWDZ\` 文件夹，内含 `CWDZ.exe`）。

## GitHub Actions 自动打 Windows 包

本机是 Mac 时，可把项目推到 GitHub 后，在仓库 **Actions → Build Windows → Run workflow** 手动触发。

约 30–60 分钟后，在运行记录的 **Artifacts** 中下载 `CWDZ-Windows-x64.zip`，解压到本机 `dist/` 即可。

工作流文件：`.github/workflows/build-windows.yml`

## 跨平台说明

- **无法在 Mac 上直接打出 Windows 的 .exe**，需在 Windows 环境运行 `build.bat`，或使用上方 GitHub Actions。
- **无法在 Windows 上直接打出 .app**，需在 macOS 运行 `build.sh`。
