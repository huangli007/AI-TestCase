# 设计文档:AI 测试用例生成 Agent(TestCase Agent)

## 1. 文档信息

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.0 |
| 创建日期 | 2026-08-08 |
| 依据 | PRD v1.2(交互形态:跨平台桌面 GUI + CLI) |
| 作者 | WorkBuddy |
| 状态 | 设计定稿 |

## 2. 设计目标与约束

### 2.1 设计目标

1. **多模态输入统一**:文本 / 图片 / 视频三类素材经解析层统一为"文本素材",后续阶段无感知差异;
2. **三阶段质量管线**:产品分析(测试点)→ 用例生成 → 质量评审,每阶段输出经 pydantic 模型校验,坏数据就地拦截;
3. **算力可外接**:OpenAI 兼容协议,文本/视觉模型分离配置,同一代码接入 DeepSeek / Qwen / OpenAI / 智谱等;
4. **跨平台一致体验**:同一套 Python 代码在 Windows / macOS 提供一致的桌面 GUI 与 CLI,平台差异收敛到适配层;
5. **可离线演示**:Mock LLM 客户端免 Key 跑通全流程,用于演示与 CI。

### 2.2 约束

| 约束 | 说明 |
|------|------|
| 语言/运行时 | Python ≥ 3.10 |
| 交互形态 | 桌面 GUI(Qt/PySide6)为主,CLI 为辅;无 Web 端 |
| 平台 | Windows 10/11、macOS 12+ |
| 外部依赖 | 用户自备 OpenAI 兼容大模型 API Key |
| 无浏览器依赖 | 全部能力本地窗口完成 |

## 3. 总体架构

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│  表现层 (Presentation)                                       │
│  ┌──────────────────────┐      ┌──────────────────────────┐  │
│  │ 跨平台桌面 GUI        │      │ CLI (main.py)            │  │
│  │ (Qt/PySide6)         │      │ argparse 参数解析         │  │
│  └──────────┬───────────┘      └───────────┬──────────────┘  │
├─────────────┼──────────────────────────────┼────────────────┤
│  应用层 (Application)                       │                │
│  ┌──────────────────────────────────────────▼────────────┐  │
│  │ TestCaseAgent(编排器):解析→分析→生成→评审→导出           │  │
│  │ Analyzer / Generator / Reviewer(三阶段管线)             │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  领域层 (Domain)                                             │
│  models.py(pydantic:ProductAnalysis/TestPoint/TestCase...)  │
│  prompts.py(三阶段 Prompt 模板,黑盒方法论注入)                │
├─────────────────────────────────────────────────────────────┤
│  基础设施层 (Infrastructure)                                 │
│  llm/(LLMClient·MockLLMClient·JSON容错)                      │
│  parsers/(text·image·video)                                 │
│  exporters/(excel·markdown·json)                            │
│  config.py(YAML+环境变量插值)                                │
├─────────────────────────────────────────────────────────────┤
│  平台适配层 (Platform Adapter) — 跨平台收敛点                 │
│  pathlib 路径 / QFileDialog / QDesktopServices / 字体适配    │
│  imageio-ffmpeg 自带二进制(免系统 ffmpeg)                    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 分层职责与依赖规则

| 层 | 职责 | 依赖 |
|----|------|------|
| 表现层 | 用户交互、进度展示、结果预览、导出触发 | 应用层 |
| 应用层 | 流程编排、阶段调度、进度回调 | 领域层 + 基础设施层 |
| 领域层 | 数据结构、Prompt 策略(纯函数,无 IO) | 仅 pydantic |
| 基础设施层 | 外部 IO(LLM API、文件解析、导出落盘) | 领域层模型 |
| 平台适配层 | 屏蔽 OS 差异 | 跨层提供工具函数 |

**依赖规则**:上层只依赖下层接口;基础设施层可替换(如换 OCR 解析器、换导出格式),不影响上层。

## 4. 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.10+ | 生态成熟、与 LLM SDK 契合、跨平台 |
| GUI 框架 | PySide6(Qt 6) | 官方跨平台、原生控件、QThread 线程模型、可打包 |
| LLM 客户端 | openai SDK(自定义封装) | 事实标准,兼容一切 OpenAI 协议服务 |
| 数据模型 | pydantic v2 | 结构化约束各阶段输出,自动校验 |
| 配置 | PyYAML + 环境变量插值 | 声明式、可版本管理、密钥走环境变量 |
| 文档解析 | python-docx / pypdf | 轻量、纯 Python |
| 图片处理 | Pillow | 压缩/编码,跨平台 |
| 视频抽帧 | imageio-ffmpeg | 自带 ffmpeg 二进制,Windows/macOS 免装系统依赖 |
| Excel 导出 | openpyxl | 样式控制(着色/冻结/换行) |
| 打包 | PyInstaller | 双平台打包为原生应用/可执行文件 |

## 5. 模块设计

### 5.1 数据模型(models.py)

统一领域对象,全部为 pydantic 模型,`model_dump()/model_validate()` 贯穿各层。

| 模型 | 关键字段 | 说明 |
|------|---------|------|
| FunctionPoint | module, feature, rules[] | 功能点及业务规则 |
| BusinessFlow | name, description | 业务流程 |
| TestPoint | id, module, name, type, description, priority, inferred | 测试点;inferred 标记推断项 |
| ProductAnalysis | product_name, product_type, target_users, core_value, modules[], business_flows[], risk_points[], test_points[] | 阶段一产物 |
| TestCase | case_id, module, test_point, title, priority, case_type, precondition, test_data, steps[], expected[] | 用例全字段 |
| ReviewResult | summary, gaps[], issues[], cases[] | 评审产物 |
| GenerationResult | product_name, analysis, cases[], review? | 端到端最终产物 |

**设计要点**:
- 优先级/类型使用 `Literal` 枚举,从模型层杜绝非法取值;
- `TestCase.steps/expected` 为数组,导出时按编号拼装,保证展示一致;
- `inferred` 字段保障"资料缺失推断"可追溯。

### 5.2 配置设计(config.py)

```
优先级: CLI 参数 > 环境变量(LLM_API_KEY 等) > config.yaml > 内置默认值
```

| 配置项 | 环境变量 | 默认 | 说明 |
|--------|---------|------|------|
| llm.base_url | LLM_BASE_URL | DeepSeek 地址 | OpenAI 兼容端点 |
| llm.api_key | LLM_API_KEY | 空 | 必填(真实模式) |
| llm.model | LLM_MODEL | deepseek-chat | 文本模型 |
| llm.vision_model | LLM_VISION_MODEL | 空(跟随 model) | 视觉模型,如 gpt-4o / qwen-vl-max |
| llm.temperature | - | 0.6 | 采样温度 |
| llm.max_retries / timeout | - | 3 / 120 | 容错参数 |
| pipeline.max_frames_per_video | - | 12 | 视频抽帧上限 |
| pipeline.frame_interval | - | 2.0s | 抽帧间隔 |
| pipeline.max_image_size | - | 1280px | 图片最长边 |
| pipeline.max_cases | - | 80 | 用例总量上限 |
| pipeline.review_enabled | - | true | 评审开关 |
| pipeline.mock_mode | - | false | 离线演示 |
| export.formats | - | [xlsx, md, json] | 导出格式 |

**机制**:YAML 值支持 `${ENV_VAR}` 插值(递归处理 dict/list),密钥永不硬编码进仓库。

### 5.3 LLM 客户端(llm/)

**接口抽象**(`LLMClient` 与 `MockLLMClient` 同构,可无缝切换):

```python
class BaseLLM(Protocol):
    @property
    def vision_enabled(self) -> bool: ...
    def complete(self, messages, *, temperature, max_tokens, model, json_mode) -> str: ...
    def complete_json(self, messages, *, temperature, max_tokens, model) -> dict: ...
    def vision_analyze(self, text, image_data_uris, *, temperature) -> dict: ...
```

**LLMClient(真实实现)**:
- 基于 openai SDK,`response_format={"type":"json_object"}` 强制结构化;
- 指数退避重试(2^n 秒,默认 3 次),空响应/异常自动重试;
- `parse_json()` 容错:剥离 ```` ```json ```` 围栏、截断到最后一个合法括号;
- `vision_analyze` 组装多模态 content(文本 + 多张 image_url data URI)。

**MockLLMClient(离线实现)**:
- 根据调用阶段(analyze/generate/review)返回内置高质量示例 JSON;
- `vision_enabled=True`,视觉分析返回固定示例描述;
- 用途:CI 测试、无 Key 演示、GUI 冒烟。

**换模型** = 改配置,零代码改动。

### 5.4 解析器(parsers/)

**统一出口**:`extract_text / analyze_images / analyze_video` 全部返回 `List[str]` 素材文本。

| 解析器 | 输入 | 处理 | 输出 |
|--------|------|------|------|
| text_parser | txt/md/csv/json/log/yaml/html/docx/pdf | 直接读取;csv 转表格;docx 提取段落+表格;pdf 逐页提取 | 文本 |
| image_parser | png/jpg/jpeg/webp/bmp/gif/tiff | Pillow 压缩到 max_image_size → base64 data URI → 视觉模型 | 结构化页面描述 |
| video_parser | mp4/mov/avi/mkv/webm/flv/wmv/m4v | ffmpeg 探时长 → 均匀抽帧(≤max_frames) → 视觉模型逐帧理解 | 视频功能/流程描述 |

**抽帧算法**(video_parser):
```
duration = probe_duration(ffmpeg -i)
n = min(max_frames, max(2, duration / frame_interval))
interval = duration / n
ffmpeg -i in -vf fps=1/interval frame_%03d.jpg
```

**容错策略**:单文件失败记录错误不中断;全部失败才终止;不支持视觉时给出明确配置指引。

### 5.5 管线(pipeline/)

三阶段 + 编排器,阶段间仅依赖领域模型。

```
parse_files(file_paths)
   → materials: List[str]
      │
      ▼
Analyzer.analyze(materials)          # 阶段一
   → ProductAnalysis(test_points)
      │
      ▼
Generator.generate(analysis)         # 阶段二
   → List[TestCase]  (case_id 归一化 TC-001 起)
      │
      ▼
Reviewer.review(analysis, cases)     # 阶段三(可开关)
   → ReviewResult(修正后 cases + 报告)
      │
      ▼
export_all(result, output_dir)       # xlsx / md / json
```

**TestCaseAgent(编排器)** 关键设计:
- `on_progress(cb)` 注入进度回调,GUI 与 CLI 共用同一管线;
- 解析阶段使用临时工作目录存放抽帧图片(output/.work/);
- 评审失败/裁撤过度时回退原用例集(兜底,保证不空跑)。

### 5.6 导出(exporters/)

| 导出器 | 产物 | 设计要点 |
|--------|------|---------|
| excel.py | {产品}_测试用例.xlsx | 4 Sheet(产品分析/测试点/用例/评审);优先级 P0~P3 背景着色;冻结首行;自动换行;列宽预设 |
| markdown.py | {产品}_测试用例.md | 摘要+测试点表+用例表(步骤/预期用 `<br>` 编号拼接)+评审说明 |
| json_exporter.py | {产品}_测试用例.json | analysis/review/cases 全量 + 生成时间戳,便于平台对接 |

统一入口 `export_all(result, output_dir, formats)`,新增格式只需注册映射。

### 5.7 桌面 GUI(gui/)

**目录规划**:
```
testcase_agent/gui/
├── __init__.py
├── app.py            # 应用入口 + 主窗口
├── worker.py         # QThread 后台执行器(信号槽)
├── platform.py       # 跨平台适配(路径/字体/打开目录/配置目录)
└── ui/
    ├── widgets.py    # 素材列表、配置面板、结果表格等可复用控件
    └── style.py      # 样式表(QSS),双平台一致外观
```

**主窗口布局**(对应 PRD 6.1):素材区(左)/ 模型配置(右)/ 输出目录 / 运行控制 / 结果选项卡。

**线程模型**:
```
GUI 线程(Qt 主循环)
   │
   └─ WorkerThread(QThread)
        ├─ signals: progress(str), finished(object), error(str)
        ├─ run(): 构造 TestCaseAgent → agent.on_progress(emit progress)
        │         → agent.run(...) → emit finished(GenerationResult)
        └─ 运行期间禁用"开始"按钮,结果到达后启用导出按钮
```

**跨平台适配**(platform.py):
| 场景 | Windows | macOS | 实现 |
|------|---------|-------|------|
| 路径 | C:\... | /Users/... | pathlib.Path 统一 |
| 配置目录 | %APPDATA% | ~/Library/Application Support | QStandardPaths.AppConfigLocation |
| 中文字体 | 微软雅黑 | PingFang SC | QFont 家族回退列表 |
| 打开目录 | explorer | open | QDesktopServices.openUrl |
| 文件对话框 | 原生 | 原生 | QFileDialog.getOpenFileNames |

### 5.8 CLI(main.py)

```
python main.py --files <f...> [--out dir] [--config yaml] [--mock] [--no-review]
                [--format xlsx md json] [--verbose] [--gui]
```

- 无参数场景校验与友好报错;进程退出码 0=成功 / 1=运行失败 / 2=参数错误;
- `--gui` 直接进入桌面界面,与 GUI 共用核心管线。

## 6. 核心流程设计

### 6.1 端到端时序

```
用户            GUI/CLI          Agent            LLM
 │   输入文件     │                 │                │
 │──────────────>│  parse_files    │                │
 │               │────────────────>│  文本/视觉/抽帧  │
 │               │                 │──vision/文本───>│
 │               │                 │<──描述─────────│
 │  进度(1/3)     │                 │                │
 │<──────────────│  Analyzer       │                │
 │               │────────────────>│──JSON 分析────>│
 │               │                 │<──ProductAnalysis
 │  进度(2/3)     │  Generator      │                │
 │<──────────────│────────────────>│──JSON 用例────>│
 │               │                 │<──List[TestCase]
 │  进度(3/3)     │  Reviewer       │                │
 │<──────────────│────────────────>│──JSON 评审────>│
 │               │                 │<──ReviewResult │
 │  导出          │  export_all     │                │
 │<──────────────│─────────────────│                │
 │  xlsx/md/json │                 │                │
```

### 6.2 异常与容错

| 场景 | 策略 |
|------|------|
| 单素材解析失败 | 记录错误,继续处理其余文件 |
| 所有素材失败 | 终止并列出全部原因 |
| LLM 超时/限流 | 指数退避重试 3 次 |
| LLM 返回非 JSON | 围栏剥离 + 截断修复;仍失败则报错并附输出预览 |
| 评审裁撤过度(0 条) | 回退使用生成阶段用例集 |
| GUI 运行中用户重复点击 | 禁用开始按钮直至完成 |
| API Key 缺失 | 明确提示配置方式或建议 Mock 模式 |

### 6.3 数据一致性

- case_id 全局唯一连续,生成与评审阶段均做归一化;
- 阶段间传递一律经过 pydantic 校验,非法数据就地拦截而非带病前进。

## 7. Prompt 设计(prompts.py)

| 阶段 | System 角色 | 关键约束 |
|------|------------|---------|
| 分析 | 15 年资深测试架构师 | 黑盒方法论;覆盖正/负/边界/权限/并发/兼容/安全/性能;8~20 测试点;缺资料推断并标 inferred;只输出 JSON |
| 生成 | 资深测试工程师 | 每测试点 2~4 条(至少 1 正 + 1 异常);步骤可操作、预期可验证;P0~P3 优先级规则;负向用例必查 |
| 评审 | 严谨测试经理 | 对照分析补漏/去重/修正/校正优先级;输出修正后完整用例集并重新编号;附总结/遗漏点/问题 |

**方法论注入**:等价类、边界值、场景法、错误推测、状态迁移、因果图,写死在 System Prompt,保证不同模型输出同质化。

## 8. 安全设计

1. **密钥管理**:API Key 支持环境变量注入;GUI 配置本地保存(配置目录,不随代码分发);日志中不输出 Key;
2. **数据边界**:素材仅发送至用户配置的 API 端点;导出产物本地落盘;
3. **脱敏**:评审/生成 Prompt 强调敏感信息(手机号/地址)脱敏展示;
4. **输入防护**:文件扩展名白名单;图片经 Pillow 压缩重编码(防畸形文件);ffmpeg 超时控制。

## 9. 性能设计

| 项 | 控制手段 |
|----|---------|
| Token 消耗 | 视频抽帧 ≤12;图片压缩 ≤1280px/JPEG;用例总量 ≤80 |
| 视频解析 | ffmpeg 抽帧带宽受 interval 约束,超时 600s |
| GUI 响应 | 解析/LLM 调用全部在 QThread,UI 不阻塞 |
| 并发 | 阶段内顺序调用(控制成本),不并发请求 LLM |

## 10. 打包与部署(双平台)

| 平台 | 命令/产物 | 说明 |
|------|----------|------|
| Windows | `pyinstaller --windowed --name TestCaseAgent run_gui.py` → TestCaseAgent.exe | 免安装分发;可用 Inno Setup 做安装包 |
| macOS | `pyinstaller --windowed --name TestCaseAgent run_gui.py` → .app | 配合 `--osx-bundle-identifier`;可再签名/公证 |
| 通用 | CLI 直接 `python main.py` 或源码分发 | 零打包即可用 |

**打包注意事项**:
- 打包需包含 imageio-ffmpeg 的 ffmpeg 二进制(hidden-import / 数据文件);
- PySide6 自动收集 Qt 插件;中文字体依赖系统,无需内置;
- 建议为 GUI 单独入口 `run_gui.py`(设置 HiDPI 属性 `AA_EnableHighDpiScaling` 后启动主窗口)。

## 11. 目录结构

```
AI-TestCase/
├── docs/
│   ├── PRD.md               # 需求文档 v1.2
│   └── DESIGN.md            # 本设计文档
├── testcase_agent/
│   ├── __init__.py
│   ├── config.py            # 配置加载
│   ├── models.py            # 领域模型(pydantic)
│   ├── prompts.py           # 三阶段 Prompt
│   ├── llm/
│   │   ├── client.py        # OpenAI 兼容客户端
│   │   └── mock_client.py   # 离线 Mock
│   ├── parsers/
│   │   ├── text_parser.py   # txt/md/docx/pdf/csv
│   │   ├── image_parser.py  # 图片→视觉模型
│   │   └── video_parser.py  # 视频→抽帧→视觉模型
│   ├── pipeline/
│   │   ├── agent.py         # TestCaseAgent 编排器
│   │   ├── analyzer.py      # 阶段一
│   │   ├── generator.py     # 阶段二
│   │   └── reviewer.py      # 阶段三
│   ├── exporters/
│   │   ├── excel.py
│   │   ├── markdown.py
│   │   └── json_exporter.py
│   └── gui/
│       ├── app.py           # 主窗口入口
│       ├── worker.py        # QThread 后台执行
│       ├── platform.py      # 跨平台适配
│       └── ui/              # 控件与样式
├── main.py                  # CLI 入口(含 --gui)
├── run_gui.py               # GUI 独立入口(HiDPI)
├── config.example.yaml      # 配置模板
├── samples/                 # 示例素材
├── scripts/
│   ├── build_windows.bat
│   └── build_macos.sh
└── requirements.txt
```

## 12. 测试策略

| 层级 | 内容 |
|------|------|
| 单元测试 | parse_json 容错、抽帧参数、excel 导出字段、模型校验 |
| 管线测试 | Mock LLM 端到端(分析→生成→评审→导出),断言产物结构 |
| GUI 冒烟 | 窗口构建、素材添加、Mock 运行、导出按钮(PySide6 pytest-qt) |
| 真实 API 验证 | 配置三家 API 跑通全流程(DeepSeek/Qwen/OpenAI) |
| 双平台验证 | Windows/macOS 各跑 CLI + GUI 冒烟 |
| 覆盖断言 | 用例字段完整率 100%、负向场景占比 ≥30%、评审开关生效 |

## 13. 变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-08-08 | 初稿:基于 PRD v1.2 的完整设计(分层架构/模块/跨平台/流程/安全/打包/测试) |
