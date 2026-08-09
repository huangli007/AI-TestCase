# TestCase Agent — AI 测试用例生成器

自动生成高质量测试用例的 Agent:上传 **文本 / 图片 / 视频** 素材,自动分析产品测试点,生成结构化测试用例(含质量评审),一键导出 Excel / Markdown / JSON。跨平台桌面 GUI(Windows / macOS)+ CLI 双入口,算力可外接任意 OpenAI 兼容大模型 API。

## 特性

- **多模态输入**:文本(txt/md/docx/pdf/csv)、图片(UI 截图/原型图)、视频(演示/录屏,ffmpeg 自动抽帧)
- **三阶段质量管线**:产品分析(测试点)→ 用例生成 → 质量评审(补漏/去重/修正)
- **黑盒方法论注入**:等价类、边界值、场景法、错误推测、状态迁移、因果图
- **模型可外接**:OpenAI 兼容协议,文本/视觉模型分离配置(DeepSeek / Qwen / OpenAI / 智谱均可)
- **跨平台桌面 GUI**:PySide6 实现,Windows 10/11 与 macOS 12+ 同一套代码
- **离线演示**:Mock 模式免 API Key 跑通全流程
- **标准产物**:Excel(4 Sheet,优先级着色)/ Markdown / JSON

## 快速开始

```bash
# 1. 安装依赖(Python >= 3.10)
pip install -r requirements.txt

# 2a. 桌面 GUI(Windows / macOS)
python run_gui.py
# 或
python main.py --gui

# 2b. 命令行(自动化/CI)
cp config.example.yaml config.yaml   # 填入 LLM_API_KEY 或使用环境变量
python main.py --files 需求文档.pdf 原型图.png 演示.mp4 --out output/

# 2c. 离线演示(无需 API Key)
python main.py --files samples/sample_prd.md --out output --mock
```

## 配置

编辑 `config.yaml`(模板见 `config.example.yaml`),支持 `${ENV}` 环境变量插值:

```yaml
llm:
  base_url: ${LLM_BASE_URL:https://api.deepseek.com/v1}
  api_key: ${LLM_API_KEY:}                 # 或直接在 GUI 中填写
  model: ${LLM_MODEL:deepseek-chat}
  vision_model: ${LLM_VISION_MODEL:}       # 图片/视频需要,如 qwen-vl-max / gpt-4o
pipeline:
  review_enabled: true                     # 质量评审开关
  mock_mode: false                         # 离线演示
  max_cases: 80
```

图片与视频解析依赖**视觉模型**:请配置支持图像的模型(如 `qwen-vl-max`、`gpt-4o`、`deepseek-vl`)。

## 输出示例

运行后 `output/` 目录生成:

| 文件 | 说明 |
|------|------|
| `{产品名}_测试用例.xlsx` | 4 Sheet:产品分析 / 测试点清单 / 测试用例 / 评审报告,P0~P3 着色 |
| `{产品名}_测试用例.md` | 摘要 + 测试点 + 用例表格 + 评审说明 |
| `{产品名}_测试用例.json` | 全量结构化产物,便于平台对接 |

## 文档

- [产品需求文档(PRD v1.2)](docs/PRD.md)
- [设计文档](docs/DESIGN.md)
- [GUI 界面预览](docs/gui_preview.png)

## 项目结构

```
testcase_agent/
├── config.py          # 配置加载(环境变量插值)
├── models.py          # 领域模型(pydantic)
├── prompts.py         # 三阶段 Prompt 工程
├── llm/               # OpenAI 兼容客户端 + Mock
├── parsers/           # 文本/图片/视频解析
├── pipeline/          # 分析 → 生成 → 评审 → 编排
├── exporters/         # Excel / Markdown / JSON
└── gui/               # 跨平台桌面界面(PySide6)
```

## 常见问题

- **图片/视频报"不支持视觉"**:在配置中设置 `vision_model`,或使用支持图像的模型
- **提示未配置 API Key**:填写 Key,或勾选 GUI 中「离线演示模式(Mock)」

## 打包发布(Windows / macOS)

### Windows(生成 exe)

```bash
# 一键打包脚本
scripts\build_windows.bat
# 或手动执行
python -m PyInstaller TestCaseAgent.spec --noconfirm --clean
```

产物:
- `dist/TestCaseAgent/TestCaseAgent.exe`(免安装,双击即用)
- `dist/TestCaseAgent-win64.zip`(整包压缩,方便拷贝分发)
- `installer/TestCaseAgent-Setup.exe`(**安装程序**:中文向导,默认装到用户目录、免管理员;自动创建开始菜单/桌面快捷方式,含卸载功能)

制作安装程序(需 Inno Setup):

```bash
"C:\Users\<用户名>\AppData\Local\Programs\InnoSetup\ISCC.exe" setup.iss
```

**注意**:spec 已禁用 UPX(`upx=False`)——UPX 压缩会破坏 Python 自带的 OpenSSL DLL,导致启动时报 `_ssl DLL load failed`。若需减小体积,请改用 `--strip` 而非 UPX。

### macOS(生成 dmg)

在 **macOS 机器**上执行:

```bash
bash scripts/build_macos.sh
```

脚本自动完成:生成 `.icns` 图标 → PyInstaller 打包 `.app` → `hdiutil` 制作 `dist/TestCaseAgent.dmg`。
用户拿到 dmg 后双击挂载、拖入「应用程序」即可安装。
> 注:如需在他人 Mac 上运行,需对 `.app` 做 codesign 签名与 notarization(公证),否则 Gatekeeper 会拦截。
