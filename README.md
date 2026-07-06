# Smart Community Security - Code Repository

2026 研华全国 AIoT 创新应用大赛 · 创新应用赛道 · 智慧城市方向

## 目录结构

```
Code/
├── datasets/        # 训练数据集（gitignore）
├── models/          # 模型权重文件（gitignore）
├── src/             # 源代码
│   ├── detect.py             # 目标检测模块
│   ├── pose.py               # 姿态估计模块
│   ├── tracker.py            # ByteTrack 目标跟踪
│   ├── roi_config.py         # 消防通道 ROI 配置
│   ├── alert_engine.py       # 告警规则引擎
│   ├── video_processor.py    # 视频流主处理管线
│   ├── visualize.py          # 可视化标注
│   └── mqtt_client.py        # MQTT 客户端（云集成）
├── configs/         # 配置文件
├── demo/            # Demo 输入/输出视频
├── docs/            # 研究文档
│   ├── preliminary_research.md  # 前期研究
│   ├── dataset_plan.md          # 数据集计划
│   └── training_guide.md        # 训练指南
├── scripts/         # 训练/运行脚本
├── requirements.txt # Python 依赖
└── README.md        # 本文件
```

## 环境搭建

```bash
conda create -n smart-community python=3.10
conda activate smart-community
pip install -r requirements.txt
```

## 快速开始

```bash
# 训练检测模型
bash scripts/train_detect.sh

# 运行 Demo 推理
python src/video_processor.py --input demo/demo_video.mp4 --output demo/demo_output.mp4
```
