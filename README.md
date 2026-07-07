# 基于 AIoT 的城市老旧小区智慧安防与消防通道联动管控系统

2026 研华全国 AIoT 创新应用大赛 — 创新应用赛道（智慧城市）

---

## 项目简介

面向老旧小区消防通道违停、通道堆物、高空抛物、异常徘徊、老人跌倒等民生痛点，构建端-边-云三层 AIoT 智慧管控方案。通过边缘 AI（NVIDIA Jetson Orin Nano）+ 深度相机 + 多传感器融合，实现消防风险的实时识别、自动告警与工单闭环管理。

**当前阶段（初赛 PoC）**：已完成单摄像头 9 类消防风险识别探头。

## 快速导航

| 我要… | 看这里 |
|--------|--------|
| 了解项目技术架构与分阶段计划 | [`documentation/ROADMAP.md`](documentation/ROADMAP.md) |
| 了解项目背景与预期成果 | [`documentation/DESCRIPTION.md`](documentation/DESCRIPTION.md) |
| **跑代码、看模块说明、模型训练** | [**`Code/README.md`**](Code/README.md) |
| 查看 AI 代理操作约定 | [`AGENTS.md`](AGENTS.md) |

## 目录结构

```
fire-risk-wise-iot/
├── Code/                   ← Python 项目（uv 管理，所有代码命令在此执行）
│   ├── src/                # 核心模块：detector, risk_engine, visualizer, main
│   ├── tests/              # 79 个测试
│   ├── configs/            # YAML 配置
│   ├── scripts/            # 训练/标注/Demo 脚本
│   ├── models/             # 模型权重（gitignored）
│   └── datasets/           # 训练数据（gitignored）
├── documentation/          # 竞赛文档：DESCRIPTION, ROADMAP, 硬件清单
├── diagrams/               # 架构图（draw.io + SVG）
├── data/                   # 推理输出报告（JSON）
└── references/             # 参赛手册、硬件数据手册
```

## 技术栈

- **检测模型**：YOLOv8n（9 类消防风险），微调至 `fire_risk_v{N}.pt`
- **边缘部署**：TensorRT + DeepStream on Jetson Orin Nano（决赛阶段）
- **云端平台**：Advantech WISE-IoT（IoTSuite + AgentBuilder + DataInsight）
- **硬件**：MIC-711D-ON + Gemini 336L + ECU-1051E + WISE 传感器

## 进度

| 阶段 | 截止 | 状态 |
|------|------|------|
| 书审 | 6/15 | ✅ |
| 初赛 PoC | 7/14 | ✅ 9 类检测探头完成 |
| 决赛部署 | 8/18 | 🔲 Jetson + WISE-IoT |
| 总决赛 | 9/19 | 🔲 |
