# 截图批量 OCR 使用说明

本工具通过 OpenAI 兼容接口识别截图。你可以让 UI-TARS 把截图保存到 `screenshots` 文件夹，监控脚本会自动识别新文件，去掉重复文字，并持续更新 Markdown 文档。公开仓库默认使用本地演示 OCR；真实的服务地址和令牌只保存在未跟踪的本地配置或环境变量中，不要提交到 Git。

## 准备截图

可以手动把截图放进 `screenshots` 文件夹，也可以让脚本自动截取当前桌面。支持 PNG、JPG、JPEG、WebP、BMP、TIF 和 TIFF。文件名中的数字会按自然顺序处理，例如 `page2.png` 会排在 `page10.png` 前面。

## 不生成安装包也可以运行

OCR 监控脚本不依赖 UI-TARS 安装包。启动本地演示 OCR 后即可直接运行：

```powershell
python .\watch_ocr.py .\screenshots
```

如果还需要从源码启动 UI-TARS，建议使用项目提供的启动脚本：

```powershell
cd .\UI-TARS-desktop-0.3.0
.\启动UI-TARS.ps1
```

这条命令会启动开发版 UI-TARS，不需要先生成 exe 安装包。


## 运行方式一：监控 UI-TARS 的截图文件夹（推荐）

先确认工作目录中的 `ocr_config.json` 或本地未跟踪配置指向可用的 OCR 服务，然后在 PowerShell 中运行：

```powershell
python .\watch_ocr.py .\screenshots
```

看到“正在监控”后，再在 UI-TARS 中发送类似这句话：

```text
把当前网页截图保存到 D:\liminghao\pycharm\file\UI_TARS_ocr\screenshots，文件名按顺序递增；截图完成后继续下一张。
```

每当文件夹里出现新的 PNG/JPG 图片，监控脚本就会自动调用 OCR，并更新：

```text
screenshots\截图 OCR 汇总.md
```

监控脚本会等待文件写入完成；按 `Ctrl+C` 停止。只处理现有图片一次可以使用：

```powershell
python .\watch_ocr.py .\screenshots --once
```

注意：监控脚本只能处理已经落盘的图片。如果 UI-TARS 只在界面中显示截图、没有真的保存成文件，需要先让 UI-TARS 执行保存文件的动作，或者手动把截图复制到该文件夹。

## 运行方式一（UI-TARS 快捷键自动落盘）

启动脚本会把 `UI_TARS_SCREENSHOT_DIR` 设置为项目的 `screenshots` 文件夹。UI-TARS 执行 `hotkey(key='win print')` 后，会把当前画面直接保存为 `page-001.png`、`page-002.png` 等文件，监控脚本会立即识别，不依赖 Windows 的“图片\屏幕截图”目录。

先开一个 PowerShell 窗口：

```powershell
python .\watch_ocr.py .\screenshots
```

然后给 UI-TARS 的任务说明写：

```text
处理当前网页时，每完成一屏就执行 hotkey(key='win print') 截图，然后继续向下滚动。不要使用 Win+Shift+S，因为它需要人工框选。
```

## 运行方式二（Windows 系统截图同步备用方案）

如果你希望使用 Windows 自己的截图文件，也可以运行下面的同步脚本。`Win+PrtScn` 必须真的在系统中生成文件，脚本才能复制它。

先开两个 PowerShell 窗口。

窗口一，同步 Windows 截图：

```powershell
python .\sync_windows_screenshots.py
```

窗口二，自动 OCR：

```powershell
python .\watch_ocr.py .\screenshots
```

然后给 UI-TARS 的任务说明写：

```text
处理当前网页时，每完成一屏就执行 hotkey(key='win print') 截图，然后继续向下滚动。不要使用 Win+Shift+S，因为它需要人工框选。
```

同步脚本会把系统截图复制为 `page-001.png`、`page-002.png` 等文件，OCR 监控脚本随后会自动解析并合并去重。

## 运行方式二：批量处理已经存在的截图

如果需要使用其他兼容服务，配置可以使用下面的格式：

```json
{
  "base_url": "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
  "api_mode": "official-api",
  "model": "PaddleOCR-VL",
  "access_token": "你的 AI Studio Access Token"
}
```

OpenAI 兼容接口会自动请求 `/v1/chat/completions`：

```json
{
  "base_url": "https://your-ocr-service.example.com/v1",
  "api_mode": "openai-compatible",
  "model": "PaddleOCR-VL-1.6-0.9B",
  "access_token": ""
}
```

然后在 PowerShell 中切换到工作目录，运行：

```powershell
python .\ocr_screenshots.py .\screenshots
```

Access Token 需要在百度 AI Studio 的 PaddleOCR API 页面获取。官方文档说明在线 API 使用 Bearer Token 鉴权，并通过异步任务返回结果。

## 多人名单、断点续跑和定时启动

项目现在提供一个 SQLite 任务队列，名单中的每个人是一条任务。队列只允许一个人员处于 `running`，每个人的截图和 OCR 结果写入独立目录，避免不同人员的病历混在一起。

先复制示例名单，不要把真实名单提交到 Git：

```powershell
Copy-Item .\名单.csv.example .\名单.csv
# 用编辑器填写 task_id、name、patient_id；birth_date 可选
notepad .\名单.csv
```

初始化和查看状态：

```powershell
python .\task_queue.py init --csv .\名单.csv --db .\queue\tasks.sqlite3
python .\task_queue.py list --db .\queue\tasks.sqlite3
```

启动队列监督器：

```powershell
.\run_queue.ps1
```

监督器会为当前人员创建 `medical_records\<task_id>`，启动截图同步和 OCR，生成 `queue\current_task.md` 提示词，并启动 UI-TARS。请把提示词复制到 UI-TARS 执行；完成并人工检查后，在监督器窗口输入 `done` 才会进入下一个人。输入 `manual` 或 `failed` 会暂停当前队列，不会自动选择同名人员、填写验证码或提交病历。

可以只处理一人后退出：

```powershell
.\run_queue.ps1 -Once
```

每天定时启动（必须在当前已登录用户的交互桌面运行）：

```powershell
.\install_queue_schedule.ps1 -RunAt 09:00
```

也可以在任务计划程序中手动配置：程序填写 `powershell.exe`，参数填写：

```text
-NoProfile -ExecutionPolicy Bypass -File "D:\liminghao\pycharm\file\UI_TARS_all\run_queue.ps1"
```

选择“仅当用户登录时运行”。电脑锁屏、注销、远程桌面断开或没有交互桌面时，不应让 UI-TARS 自动操作医院网页。队列数据库、真实名单、提示词和病历截图都已加入 `.gitignore`；不要把这些文件上传到 GitHub。病历属于敏感健康信息，只能在获得授权的内部系统中使用，并按公司保留期限清理。

## 没有医院系统时：运行本地演示系统

项目还准备了完全虚构的本地测试系统和 OCR 模拟服务，不会访问外网，也不会识别或保存真实病历。

窗口一，启动演示网页：

```powershell
.\start_demo_system.ps1
```

浏览器打开 `http://127.0.0.1:8765`，账号和密码都是 `demo`。页面中有两位演示人员，其中 `DEMO-001` 有两份演示记录。

窗口二，启动本地 OCR 模拟服务：

```powershell
.\start_demo_ocr_server.ps1
```

窗口三，准备演示名单并启动一人队列：

```powershell
python .\task_queue.py init --csv .\demo_名单.csv --db .\queue\demo-tasks.sqlite3
.\run_queue.ps1 `
  -ListPath .\demo_名单.csv `
  -DatabasePath .\queue\demo-tasks.sqlite3 `
  -OutputRoot .\medical_records\demo `
  -PromptFile .\queue\demo-current_task.md `
  -OcrConfig .\demo_ocr_config.json `
  -StartUiTars:$false `
  -Once
```

然后把 [demo_test_prompt.md](demo_test_prompt.md) 的内容复制到 UI-TARS。完成截图后在队列窗口输入 `done`，检查：

```powershell
Get-ChildItem .\medical_records\demo\001
Get-Content .\medical_records\demo\001\OCR.md -Encoding UTF8
python .\task_queue.py list --db .\queue\demo-tasks.sqlite3
```

OCR 模拟服务返回固定演示文本，只用于验证接口和文件流转；要测试真实 OCR，请通过 `-OcrConfig .\ocr_config.local.json` 指向你有权使用的服务。`ocr_config.local.json` 已加入 `.gitignore`，不要上传。

若不想把 Token 以明文保存在 JSON 文件，可以使用环境变量：

```powershell
$env:PADDLEOCR_ACCESS_TOKEN = "你的 AI Studio Access Token"
python .\ocr_screenshots.py .\screenshots
```

也可以使用环境变量设置模型名称：

```powershell
$env:PADDLEOCR_MODEL = "PaddleOCR-VL-1.6-0.9B"
python .\ocr_screenshots.py .\screenshots
```

指定输出文件时添加 `--output`：

```powershell
python .\ocr_screenshots.py .\screenshots --output .\识别结果.md
```

## 运行方式三：由 Python 截取当前桌面后立即 OCR

只有在你明确需要 Python 自己截屏时才使用下面命令：

```powershell
python .\ocr_screenshots.py --capture --output .\当前屏幕 OCR.md
```

该命令会先把当前桌面保存为 `screenshots\自动截图.png`，然后提交这张图片进行 OCR。

默认结果保存在截图文件夹里的 `截图 OCR 汇总.md`。识别失败的图片会显示错误，脚本会继续处理剩余图片，并把成功结果写入文档。

## 接口文档

[PaddleOCR 官方在线 API 文档](https://www.paddleocr.ai/latest/en/version3.x/inference_deployment/serving/paddleocr_official_api/python.html)
