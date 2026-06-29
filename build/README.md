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
- 凭证模板与项目映射：`config/voucher/`（停简单 / 科拓，已打入安装包，生成凭证时自动使用）
- 本地覆盖：在程序目录下 `config/local.yaml`（可复制 `local.yaml.example` 后修改账号、路径）
- 数据目录：Windows 默认 `D:/CWDZ/`（下载、对账结果、凭证输出）；macOS 为程序目录下 `data/`

## 体积说明

安装包约 **300MB+**（含 Chromium 浏览器运行时），属正常现象。

## Windows 压缩包

在 Windows 打包完成后执行：

```bat
build\package_release.bat
```

生成 `dist\CWDZ-Windows-x64.zip`（解压后顶层为 `CWDZ\` 文件夹，内含 `CWDZ.exe`）。

## GitHub Actions 自动打 Windows 包

### 一键触发（推荐）

1. 安装 [GitHub CLI](https://cli.github.com/)（或 `brew install gh`）
2. 在终端登录（会打开浏览器）：

```bash
gh auth login -h github.com -p https -w
```

3. 在项目目录执行：

```bash
chmod +x build/trigger_windows_build.sh
./build/trigger_windows_build.sh
```

脚本会：创建/推送 GitHub 仓库 → 触发 **Build Windows** workflow → 等待完成 → 下载 `dist/CWDZ-Windows-x64.zip`。

私有仓库默认名 `CWDZ`，可通过环境变量改：

```bash
GITHUB_REPO_NAME=财务对账工具 GITHUB_REPO_VISIBILITY=private ./build/trigger_windows_build.sh
```

### 网页手动触发

已推送代码后，打开仓库 **Actions → Build Windows → Run workflow**，约 30–60 分钟后在 **Artifacts** 下载 `CWDZ-Windows-x64.zip`。

工作流文件：`.github/workflows/build-windows.yml`

## 跨平台说明

- **无法在 Mac 上直接打出 Windows 的 .exe**，需在 Windows 环境运行 `build.bat`，或使用上方 GitHub Actions。
- **无法在 Windows 上直接打出 .app**，需在 macOS 运行 `build.sh`。
