"""Generate competition entry Word document for TRAE SOLO Vibecoding contest."""

from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

doc = Document()

# Title
title = doc.add_heading('TRAE SOLO Vibecoding 参赛作品：重逢', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph('—— 让每个人都能用 AI 拥抱思念').alignment = WD_ALIGN_PARAGRAPH.CENTER

# 1. 摘要
doc.add_heading('1. 摘要', level=1)
doc.add_paragraph(
    '本项目使用 TRAE SOLO 开发了一款名为「重逢」的桌面端 AI 数字陪伴软件。'
    '针对目前开源社区中 AI 陪伴 Skill 部署门槛高、普通人难以使用的问题，'
    '我利用 SOLO 快速完成了从需求设计、前后端开发到桌面打包的全流程，'
    '将其打磨为一款开箱即用、温润极简的独立桌面应用，'
    '让没有任何编程经验的用户，也能通过导入亲人聊天记录来生成专属 AI 数字亲人，寄托思念。'
)

# 2. 背景
doc.add_heading('2. 背景', level=1)
doc.add_paragraph(
    '我是一名计算机专业大二学生，平时也会以视频 UP 主的身份记录技术实践与生活。'
    '近期"前女友/前同事 Skill"等数字克隆项目在技术圈爆火，让我联想到可以用 AI 帮助人们缅怀逝去的亲人。'
)
doc.add_paragraph(
    '但我面临一个巨大的挑战：技术壁垒。'
    '目前绝大多数同类项目以命令行 Skill 形式存在 GitHub 上，普通用户需要配置 Python 环境、'
    '安装依赖、编写 System Prompt——光是"打开终端"这一步就劝退了大多数人。'
    '我需要一个工具帮我快速突破界面开发和桌面端打包的繁琐流程，把冰冷的 Skill 变成普通人触手可及的温暖工具。'
    'TRAE SOLO 在我的流程中扮演了"全能搭档"的角色——不仅帮我拆解任务、设计架构，'
    '还能在开发过程中实时审查代码、发现 bug 并提出修复方案。'
)

# 3. 实践过程
doc.add_heading('3. 实践过程', level=1)

doc.add_heading('3.1 需求拆解：让 SOLO 真正理解"我要做什么"', level=2)
doc.add_paragraph(
    '作为一个没有完整项目经验的大二学生，面对"桌面端 + React 前端 + Python RAG 后端 + 本地向量数据库"'
    '这样的技术栈组合，一开始是懵的。我的策略是：先把项目的完整愿景、目标用户、核心使用流程、'
    '甚至 UI 情绪基调全部告诉 SOLO，并明确告诉它"有不懂的地方及时问我"。'
)
doc.add_paragraph(
    'SOLO 接收需求后没有直接写代码，而是启动了 Brainstorming 流程——先用多轮对话和我对齐理解，'
    '确认了"真正的桌面应用（Electron 打包，不是网页）、BYOK 付费模式、极简温润 UI、本地全离线运行"等关键约束。'
    '这个阶段我反复调整了提示词 3-4 次，才让 SOLO 完全理解"Grief Tech 悲伤科技"的产品调性——'
    '它不是普通聊天软件，UI 上不能出现终端代码框、技术参数面板、红色报错弹窗等极客元素。'
)

doc.add_heading('3.2 架构决策：在 SOLO 建议的基础上自己做判断', level=2)
doc.add_paragraph(
    'SOLO 最初推荐的是 Tauri + Next.js + Python 微服务架构。但我仔细审查后发现：'
    'Tauri 在中国 Windows 环境下的兼容性存在风险（WebView2 版本依赖、杀软误报），'
    '且 MVP 阶段不值得为轻量化牺牲生态成熟度。'
    '最终我决定采纳 SOLO 的建议框架但替换关键选型：Electron 替代 Tauri，React + Vite 替代 Next.js。'
    'SOLO 尊重了这个决策，后续所有代码都基于新架构生成。'
)
doc.add_paragraph(
    '最终技术栈：Electron（桌面壳）+ React + TypeScript（前端）+ Python FastAPI（后端）+ '
    'ChromaDB（向量库）+ BGE-small-zh-v1.5（嵌入模型）+ DeepSeek API（LLM）。'
)

doc.add_heading('3.3 UI 设计：用 Visual Companion 可视化协作', level=2)
doc.add_paragraph(
    'UI 调性是这个项目最不能妥协的部分。SOLO 提供了 Visual Companion 功能——'
    '它可以在浏览器中实时渲染 UI 模型，我一边描述想要的感觉，它一边推送到浏览器给我看。'
    '我们反复迭代了 7 个版本：'
    '"让他离你更近一些"作为标题 → 头像在 API Key 上方 → 维持温润语气 → '
    '所有引导文案从"指令式"改为"好奇式"（"你怎么称呼他？"而非"请输入称呼"）。'
    '这个过程如果没有可视化辅助，靠文字沟通至少要花 3 倍时间。'
)

doc.add_heading('3.4 核心开发：子代理驱动 + 15 任务并行', level=2)
doc.add_paragraph(
    'SOLO 将整个项目分解为 15 个独立任务：Python 后端配置管理 → SQLite 对话存储 → '
    'RAG 引擎（LangChain 分块 + BGE 嵌入 + ChromaDB 检索）→ dot-skill 人格蒸馏 → '
    'Agent 循环 + 纠错检测 → FastAPI 端点 → Electron 主进程 → '
    'React 组件（5 屏引导向导 + 聊天 + 设置 + 温润样式）。'
)
doc.add_paragraph(
    '它启动了 Subagent-Driven Development 模式，每个任务派一个独立子代理执行，'
    '执行完毕后自动触发两阶段审查（Spec 合规审查 → 代码质量审查），发现问题立即修复。'
    '整个后端 7 个任务 + 前端 6 个任务 + 集成 2 个任务，全部在一个对话 Session 中完成。'
)

doc.add_heading('3.5 踩坑实录：SOLO 帮我发现了什么', level=2)

p = doc.add_paragraph()
r = p.add_run('坑 1：人格蒸馏完全失效。')
r.bold = True
doc.add_paragraph(
    '用户填完所有信息、上传聊天记录后，AI 回复"你好，我是你的关系分析师，请告诉我你想分析谁"。'
    'SOLO 排查发现根因：我直接用了开源项目 dot-skill 的 Prompt 文件，但那些 Prompt 设计给交互式聊天 Agent 用的'
    '（一问一答收集信息），不适合我们的表单一次性提交场景。LLM 收到的指令是"向用户提问"而不是"分析已有信息"。'
    '修复：重写了蒸馏流水线，使用 dot-skill 的原生 persona_analyzer.md + persona_builder.md 做结构化分析。'
)

p = doc.add_paragraph()
r = p.add_run('坑 2：头像反复闪烁。')
r.bold = True
doc.add_paragraph(
    '聊天界面每条 AI 消息旁的头像，在用户发送消息后会突然变回默认灰色圆圈，直到 AI 回复完才恢复。'
    'SOLO 发现原因：头像 URL 用了 Date.now() 每次渲染都生成新 URL，浏览器每次重新下载图片，加载期间露出灰色底。'
    '修复：把头像 URL 存到 React state，只在首次加载时获取一次。'
)

p = doc.add_paragraph()
r = p.add_run('坑 3：AI 只有单句记忆。')
r.bold = True
doc.add_paragraph(
    '测试时发现 AI 完全不记得上一句说了什么——每次对话都是孤立的。'
    'SOLO 定位到 agent/loop.py 里只传了 system prompt + 当前消息给 DeepSeek，没有附带对话历史。'
    '修复：在 messages 数组中注入最近 30 条对话记录。'
)

p = doc.add_paragraph()
r = p.add_run('坑 4：智能追问太琐碎。')
r.bold = True
doc.add_paragraph(
    '聊天记录分析完成后，LLM 会反问用户一些它不确定的实体。'
    '但早期版本问得太细——比如"那个粉是指什么食物或物品?"——用户自己都记不清了。'
    '修复：增加了筛选规则，只问反复出现且有情感意义的实体，最多 3 个。'
)

# 4. 成果展示
doc.add_heading('4. 成果展示', level=1)
doc.add_paragraph(
    '开源仓库：https://github.com/yangdongchen66-boop/reunion-skill'
)
doc.add_paragraph('核心功能：')
features = [
    '5 屏对话式引导：借鉴 MBTI 问卷思路，把"描述他"拆成基本信息 → 性格速写 → 一个记忆，每屏只问 2-3 个具体问题',
    'dot-skill 人格蒸馏：上传聊天记录后，LLM 提取表达 DNA、情绪触发点、冲突模式、记忆印记 4 个维度，生成 6 层结构化 persona',
    '本地 RAG 记忆检索：聊天记录分块 → BGE 向量嵌入 → ChromaDB 存储，对话时检索 Top-5 相关记忆作为回答锚点',
    'Agent 循环：用户消息 → 意图分类（闲聊/记忆搜索/纠错）→ 选择性 RAG 检索 → 拼装 Prompt → DeepSeek 回复',
    '角色内纠错：用户说"他才不会这么说"时，AI 以角色口吻自然改口（"啊…太久没见脑子有点乱"），不暴露系统身份',
    '头像 + 温润 UI：聊天页像微信，支持上传头像，全局暖色调，所有错误提示都不使用红色感叹号',
]
for f in features:
    doc.add_paragraph(f, style='List Bullet')

# 5. 效果与总结
doc.add_heading('5. 效果与总结', level=1)

doc.add_paragraph(
    '整个项目从零到可运行 MVP，大约用了 2-3 天（课余时间）。'
    '如果让我一个大二学生独立完成——学习 Electron 打包、Python RAG 管线、React 组件设计、'
    'dot-skill 蒸馏原理——至少需要 2-3 周，而且代码质量远不如现在。'
)

doc.add_heading('5.1 SOLO 在我流程中的角色', level=2)
roles = [
    '架构师：帮我做技术选型、设计数据流、规划文件结构',
    '设计师：通过 Visual Companion 实时渲染 UI 模型，7 轮迭代确定最终设计',
    '全栈工程师：生成 22 个文件的完整代码，覆盖 Electron / React / Python / SQLite / ChromaDB',
    'Code Reviewer：每次任务完成后自动进行 Spec 合规审查 + 代码质量审查',
    'Debug 搭档：头像闪烁、蒸馏失效、上下文丢失——每个 bug 都精准定位到具体文件和行号',
]
for role in roles:
    doc.add_paragraph(role, style='List Bullet')

doc.add_heading('5.2 可复用的方法', level=2)
methods = [
    'Plan 先行：不要上来就写代码，先让 AI 完整理解你的产品愿景和情绪基调，生成一份详细 Spec 再动手',
    '多轮对齐：如果你的项目有特殊的产品调性（如 Grief Tech），花时间让 AI 理解"什么不能做"比"什么要做"更重要',
    '子代理驱动：大项目拆成独立任务，每个任务独立子代理 + 两阶段审查，比一次性生成全部代码质量高得多',
    '原生 Prompt 优先：AI 领域的成熟方案（如 dot-skill）有精心调试的 Prompt，不要自己重写，直接用原生的更可靠',
    'Visual Companion：UI 设计的沟通成本用可视化降维，文字描述界面细节的效率极低',
]
for m in methods:
    doc.add_paragraph(m, style='List Bullet')

doc.add_paragraph(
    '最终，SOLO 不仅帮我实现了一个产品，更重要的是让我这个大二学生真正完成了一个可运行、'
    '有温润体验、技术架构合理的桌面应用。从 CLI Skill 到 .exe 桌面软件，SOLO 帮我跨过了那道最难的工程门槛。'
)

# Save
desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
filepath = os.path.join(desktop, '重逢_TRAE_SOLO_参赛报名.docx')
doc.save(filepath)
print(f'Saved to: {filepath}')
