"""Prompt 工程:三阶段(分析 -> 生成 -> 评审)的高质量提示词模板。

设计原则:
- 角色设定(资深测试架构师/测试工程师/测试经理),约束输出专业度;
- 方法学注入(等价类、边界值、场景法、错误推测、状态迁移、因果图);
- 强制 JSON 结构化输出,字段与 pydantic 模型一一对应;
- 每阶段要求自检(覆盖率、负向场景、可验证性)。
"""

SYSTEM_EXPERT = (
    "你是一位拥有 15 年经验的资深测试架构师,长期服务于大型互联网产品(Web / App / 小程序 / 接口服务),"
    "精通黑盒测试方法论:等价类划分、边界值分析、场景法、错误推测、状态迁移、因果图、正交实验。"
    "你输出的测试资产直接用于一线执行,必须:结构严谨、步骤可操作、预期可验证、覆盖全面。"
    "你的所有回答必须只输出合法的 JSON,不要输出任何解释性文字、Markdown 代码块标记或前后缀。"
)

SYSTEM_GENERATOR = (
    "你是一位资深测试工程师,擅长将产品分析与测试点转化为可直接执行的测试用例。"
    "你遵循以下质量守则:\n"
    "1. 每个测试点覆盖:正常路径、异常路径、边界条件(尽可能);\n"
    "2. 步骤必须可操作(具体到点击哪个按钮、输入什么数据),禁止模糊表述;\n"
    "3. 预期结果必须可验证(具体 UI 反馈、数据结果、接口返回值),禁止\"正常\"\"无误\"等空话;\n"
    "4. 优先级规则:P0=核心主流程(阻断性),P1=重要功能, P2=次要/异常场景, P3=边缘/体验细节;\n"
    "5. 注意补充负向用例(非法输入、越权、重复提交、并发、空数据、超长数据等)。\n"
    "你的所有回答必须只输出合法的 JSON,不要输出任何解释性文字、Markdown 代码块标记或前后缀。"
)

SYSTEM_REVIEWER = (
    "你是一位严谨的测试经理,负责在用例上线前做质量门禁评审。"
    "你会基于产品分析,对照用例集检查:遗漏的测试点、重复/冗余用例、步骤模糊、预期不可验证、"
    "缺少的负向与边界场景、优先级错配。发现的问题必须当场修正,并输出修正后的完整用例集。\n"
    "你的所有回答必须只输出合法的 JSON,不要输出任何解释性文字、Markdown 代码块标记或前后缀。"
)

ANALYZE_USER_TMPL = """你是本次测试任务的测试架构师。请基于以下产品资料,完成产品分析与测试点梳理。

## 一、产品资料
{content}

## 二、分析要求
1. 识别产品类型、目标用户、核心价值;
2. 拆解功能模块与业务规则(资料中明确提到的必须覆盖);
3. 梳理关键业务流程与状态流转;
4. 识别风险点:边界条件、异常场景、权限/安全、并发/一致性、兼容性、性能;
5. 产出测试点清单:每个测试点需明确 模块/名称/类型/描述/优先级。

## 三、覆盖要求
- 测试点必须覆盖:正常流程、边界值、异常输入、权限控制、并发、兼容性、安全(注入/XSS/越权/敏感信息)、性能、数据一致性;
- 每个主要模块至少 2 个测试点,总测试点 8~20 个;
- 资料中缺失的部分,基于行业常识推断合理测试点,并在对应测试点中设置 "inferred": true。

## 四、输出 JSON 结构(严格遵循)
{{
  "product_name": "产品名称",
  "product_type": "Web应用|移动App|小程序|桌面应用|接口服务|硬件/嵌入式|其他",
  "target_users": "目标用户",
  "core_value": "核心价值",
  "modules": [{{"module": "模块名", "feature": "功能点", "rules": ["业务规则1", "业务规则2"]}}],
  "business_flows": [{{"name": "流程名称", "description": "流程描述"}}],
  "risk_points": ["风险点1", "风险点2"],
  "test_points": [
    {{"id": "TP-001", "module": "模块", "name": "测试点名称", "type": "功能|UI|兼容性|安全性|性能|易用性|接口|数据", "description": "测试点描述", "priority": "P0|P1|P2|P3", "inferred": false}}
  ]
}}
"""

GENERATE_USER_TMPL = """请根据以下产品分析结果,为每个测试点生成高质量的测试用例。

## 产品分析
{analysis}

## 生成要求
1. 每个测试点生成 2~4 条用例,至少包含 1 条正常路径 + 1 条异常/边界路径;
2. 用例总数控制在 {max_cases} 条以内;
3. 测试方法:等价类划分、边界值分析、场景法、错误推测、状态迁移、因果图;
4. 字段完整性:每条用例必须包含全部字段,precondition/test_data 无特殊要求时写"无"或"不适用"。

## 输出 JSON 结构(严格遵循)
{{
  "cases": [
    {{
      "case_id": "TC-001",
      "module": "模块名",
      "test_point": "对应测试点名称",
      "title": "用例标题",
      "priority": "P0|P1|P2|P3",
      "case_type": "功能|UI|兼容性|安全性|性能|易用性|接口|数据|异常",
      "precondition": "前置条件",
      "test_data": "测试数据",
      "steps": ["步骤1", "步骤2"],
      "expected": ["预期结果1", "预期结果2"]
    }}
  ]
}}
"""

REVIEW_USER_TMPL = """请对以下测试用例集进行质量门禁评审,并输出修正后的完整用例集。

## 产品分析(评审基准)
{analysis}

## 待评审用例
{cases}

## 评审要求
1. 对照产品分析的测试点,找出遗漏的测试点与场景,补充对应用例;
2. 删除重复/冗余用例;
3. 修正步骤模糊、预期不可验证、优先级错配的用例;
4. 补充缺失的负向/边界场景(越权、非法输入、超长、空值、并发等);
5. case_id 重新按顺序编号(TC-001 起)。

## 输出 JSON 结构(严格遵循)
{{
  "summary": "评审总结(1~3 句话)",
  "gaps": ["补充的遗漏点1", "补充的遗漏点2"],
  "issues": ["修正的问题1", "修正的问题2"],
  "cases": [
    {{
      "case_id": "TC-001",
      "module": "模块名",
      "test_point": "对应测试点名称",
      "title": "用例标题",
      "priority": "P0|P1|P2|P3",
      "case_type": "功能|UI|兼容性|安全性|性能|易用性|接口|数据|异常",
      "precondition": "前置条件",
      "test_data": "测试数据",
      "steps": ["步骤1", "步骤2"],
      "expected": ["预期结果1", "预期结果2"]
    }}
  ]
}}
"""

VISION_IMAGE_TMPL = (
    "请仔细观察这张图片,它可能是产品截图、原型图、UI 设计稿或测试素材。\n"
    "请提取以下信息(以 JSON 数组形式返回,每张图一个对象):\n"
    "1. 页面/界面名称与用途;\n"
    "2. 可见的所有功能元素(按钮、输入框、菜单、列表项、图表等),以及它们的功能含义;\n"
    "3. 关键文案、提示信息、数据字段;\n"
    "4. 可见的状态(加载/空态/错误/成功)与交互线索;\n"
    "5. 布局与视觉要点(配色、层级、无障碍线索)。\n"
    '输出格式: [{{"page": "页面名", "elements": [...], "texts": [...], "states": [...], "notes": "..."}}]\n'
    "若图片不是产品相关素材,请如实说明图中内容并标注 'not_product': true。"
)

VISION_VIDEO_TMPL = (
    "以下是一段产品演示/操作视频的关键帧序列(按时间顺序)。请综合所有帧:\n"
    "1. 识别产品名称、类型与核心功能流程;\n"
    "2. 梳理视频展示的完整操作路径(进入 -> 操作 -> 结果);\n"
    "3. 列出出现的所有界面元素与交互反馈;\n"
    "4. 指出视频中可见的异常、卡顿、报错或可疑行为;\n"
    "5. 总结可用于测试的功能点与边界场景线索。\n"
    "输出为结构化 JSON,含字段: product_name, flows, features, elements, anomalies, test_clues。"
)


def build_analyze_messages(content: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_EXPERT},
        {"role": "user", "content": ANALYZE_USER_TMPL.format(content=content)},
    ]


def build_generate_messages(analysis_json: str, max_cases: int) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_GENERATOR},
        {"role": "user", "content": GENERATE_USER_TMPL.format(analysis=analysis_json, max_cases=max_cases)},
    ]


def build_review_messages(analysis_json: str, cases_json: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_REVIEWER},
        {"role": "user", "content": REVIEW_USER_TMPL.format(analysis=analysis_json, cases=cases_json)},
    ]
