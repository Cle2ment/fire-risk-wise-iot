# ROADMAP.md

> **项目：基于 AIoT 的城市老旧小区智慧安防与消防通道联动管控系统**
> **赛事：2026 研华全国 AIoT 创新应用大赛 — 创新应用赛道（智慧城市）**
**生成日期：2026-07-14**
**版本：v2.2 — 更新 WISE-IoT MQTT 集成进度**

---

## 0. 文档说明

本文档基于以下信息源交叉验证撰写：

- 大赛红头文件（中机电协〔2026〕23 号）+ 官网
- 官方推荐硬件清单 + 数据手册
- NVIDIA Jetson / Ultralytics YOLO26 官方推理基准
- ORBBEC 官网 + GitHub 开源库
- Advantech WISE-IoT 云平台技术文档
- **b01** — 前序对话研究（赛事规则、硬件参数、产品形态分析）

---

## 1. 产品形态总览

### 1.1 核心结论：交付软硬件一体化 AIoT 系统，而非纯算法

![竞赛四阶段路线图](../diagrams/competition_timeline/competition_timeline.svg)

### 1.2 五层系统架构

| 层级 | 组件 | 形态 |
|------|------|------|
| 感知层 | Gemini 336L 深度相机 ×2-3, WISE-4012E/4051 传感器 | 物理硬件 |
| 边缘 AI 层 | MIC-711D-ON（Jetson Orin Nano 8GB, 67TOPS） | TensorRT + DeepStream |
| 通信层 | EKI-2525-BE + ECU-1051E + MQTT | 数据上云 |
| 管控层 | IoTSuite (Dashboard+SaaS Composer+Notification) + AgentBuilder + DataInsight | 实时监控 + 工单派发 + AI决策 |
| 治理层 | EdgeLink + REST API / Webhook | 街道智慧城市平台对接 |

---

## 2. 硬件选型方案

### 2.1 核心硬件

| 项目 | 推荐 | 关键参数 |
|------|------|----------|
| **边缘 AI 主板** | **MIC-711D-ON3A1** | Orin Nano 8GB, 67TOPS, 2×GMSL2.0, 125×125×51mm |
| **深度相机 ×2** | **Gemini 336L** | IP65, -10~50℃, 主动+被动立体, 全局快门, 0.17-20m+ |
| 协议网关 | ECU-1051E | RS-232/485, MQTT |
| 交换机 | EKI-2525-BE | 5口百兆 |
| 传感器 | WISE-4012E+4051 | 模拟/数字量采集 |

### 2.2 预算

| 项目 | 预估成本 | 经费来源 |
|------|---------|---------|
| MIC-711D-ON3A1 | ¥2500-3500 | 专项产品申请 |
| Gemini 336L ×2 | ¥2400-3000 | 专项产品申请 |
| ECU-1051E | ¥800-1200 | 普惠 2000 补贴 |
| 其他 | ¥850-1100 | 普惠补贴 |
| **合计** | **¥6550-8800** | 自付约 ¥2000-4000 |

---

## 3. AI 算法实现路径

### 3.1 资源预算（Orin Nano 8GB）

| 组件 | GPU 时间 | 内存 |
|------|----------|------|
| YOLO26n 检测 (5类) TRT FP16 | **4.57ms** | ~300MB |
| YOLO26n-pose TRT FP16 | **~5ms** | ~300MB |
| ByteTrack + 逻辑 (CPU) | ~2ms | ~80MB |
| **总计** | **~10ms** | **~700MB** |

> **GPU 利用率 <15%，有余量处理 3-4 路摄像头。**

### 3.2 YOLO26n 统一检测器（5 类）

![YOLO26n统一检测器](../diagrams/yolo26n_detector/yolo26n_detector.svg)

> 推理: 4.57ms → 219FPS | 模型: ~8MB

### 3.3 各任务详细方案

#### 违停检测
- YOLO26n + 静态 ROI 区域 + 车辆停留 >30s → 告警
- 地磁传感器交叉验证

#### 高空抛物
- YOLO26n 高分辨率 (1280×1280) ~55-70FPS
- 数据增强: Mosaic + Copy-Paste + 随机缩放
- SAHI 分块推理辅助

#### 徘徊检测
- YOLO26n person 检测 + ByteTrack (CPU, ~1ms)
- 判定：track 存活 >30s AND 质心位移 <2m

#### 跌倒检测
- YOLO26n-pose TRT FP16, 17关键点, ~150+FPS
- 几何判定：身体水平 + 垂直速度突变 + 接近地面

### 3.4 训练 → 部署流程

![训练到部署流程](../diagrams/training_deploy_flow/training_deploy_flow.svg)

---

## 4. 软件平台架构

### 4.1 端-边-云架构图

![端-边-云架构](../diagrams/edge_cloud_architecture/edge_cloud_architecture.svg)

### 4.2 关键软件栈

| 层级 | 组件 | 用途 |
|------|------|------|
| 系统 | JetPack 6.2 (Super) | BSP + CUDA + TensorRT |
| 视频 | DeepStream 7.1 | 多路视频 HW 解码 |
| 推理 | TensorRT 10.x | YOLO26n/pose FP16 推理 |
| 训练 | Ultralytics YOLO26 | 训练 + TensorRT 导出 |
| 跟踪 | ByteTrack (CPU) | 多目标跟踪 + 徘徊判定 |
| 相机 | Orbbec SDK v2 | Gemini 336L 深度相机驱动 |
| 边缘 | IoT Edge Runtime | MQTT Bridge + 边缘预处理 |
| 云端 | IoTSuite | Dashboard + SaaS Composer + Notification |
| AI Agent | AgentBuilder | 自动工单派发 + LLM 处置建议 |
| 分析 | DataInsight | 周报/月报自动生成 + 趋势分析 |
| 运维 | DeviceOn | 边缘设备健康监控 |

### 4.3 MQTT Topic 设计

边缘端推理完成后，告警数据通过以下 Topic 结构经由 ECU-1051E Broker 上云：

```
smart_community/{community_id}/
├── alerts/
│   ├── fire_lane_violation     ← 消防通道违停告警
│   ├── channel_obstruction     ← 通道堆物告警
│   ├── abnormal_loitering      ← 异常徘徊告警
│   ├── high_altitude_throwing  ← 高空抛物告警
│   └── elderly_fall            ← 老人跌倒告警
├── sensors/
│   ├── smoke_detector/{id}     ← 烟感数据
│   ├── temperature/{id}        ← 温感数据
│   └── geomagnetic/{id}        ← 地磁数据
├── devices/
│   ├── {id}/status             ← 设备心跳/状态
│   └── {id}/telemetry          ← GPU温度/CPU使用率
└── events/
    ├── alert_resolved/{id}     ← 告警已处置
    └── device_offline/{id}     ← 设备离线通知
```

> 详细 JSON Payload 设计见 `code/docs/wise_iot_project_integration_analysis.md` §4.2。

### 4.4 延伸阅读

- [WISE-IoT 平台详细使用说明](../code/docs/wise_iot_platform_usage_guide.md) — 7 大核心服务介绍、6 步使用指南
- [WISE-IoT 与项目联动分析](../code/docs/wise_iot_project_integration_analysis.md) — 11 项需求匹配、架构融合、评审加分分析

---

## 5. 按竞赛阶段分步计划

### 阶段1：书审（当前→6/15）
- 技术方案文档 + PPT + PoC 框架

### 阶段2：初赛（6月→7/14）
- YOLOv8n 训练 + TensorRT 导出 + 推理管线 + Demo 视频 ✅ （9 类消防风险检测 PoC 已完成）
- **WISE-IoT MQTT 集成 ✅**（7/14 完成）：
  - IoTSuite v2.0.6 设备模型 FireRiskDetector 已注册（8 属性点）
  - 设备 fire-risk-pc-01 已注册（DCCS 直连，MQTT 协议）
  - DCCS SDK Cloud Publisher 脚本已实现（`scripts/sdk_cloud_publisher.py`）
  - paho-mqtt 备用发布器已实现（`scripts/mqtt_cloud_publisher.py`）
  - Dashboard DataHub-SimpleJson 数据源已创建（ID:365），待填入 DataHub URL

### 阶段3：决赛（7月→8/18）
- **硬件申请与部署**：申请 MIC-711D-ON + Gemini 336L + ECU-1051E
- **TensorRT 迁移**：PC 训练好的 .pt → .engine，部署到 Jetson
- **DeepStream 管线**：配置 nvv4l2decoder → nvinfer → nvtracker → nvdsosd
- **MQTT 上云**（✅ 初赛已提前完成 PC 端）：
  - SDK Publisher → DCCS → DataHub → Dashboard（`sdk_cloud_publisher.py`）
  - 备用：paho-mqtt → ECU-1051E Broker → EdgeLink → DataHub
- **IoTSuite 对接**：
  - ① Dashboard 搭建 ✅（v2 完成，12 面板，DataHub-SimpleJson 数据源已创建）
  - ② MQTT Topic 配置 + DataHub 数据接入 ✅（设备模型+Topic 已配置，待填入 DataHub URL）
  - ③ SaaS Composer 工单规则配置（1天）
  - ④ Notification 推送通道（0.5天）
- **Gemini 336L 集成**：Orbbec SDK 接入，GMSL2.0/USB3.0 驱动调试

### 阶段4：总决赛（8月→9/19）
- DeepStream 3-4 路视频并行推理优化
- DataInsight 周报/月报模板配置
- Dashboard 美化 + SaaS Composer 界面打磨
- 全链路压力测试（模拟 24h 运行）+ 稳定性 bug 修复
- 现场演示准备：答辩 PPT + 便携演示箱

---

## 6. 风险矩阵

| 风险 | 对策 |
|------|------|
| Gemini 336L 申请被拒 | USB 摄像头 + 纯 RGB 检测备选 |
| 高空抛物小目标检测差 | SAHI 分块推理 + 1280 高分辨率训练 |
| 室外光照干扰 | 336L IR-Pass 滤镜 + 图像增强预处理 |
| 答辩场地限制 | 便携演示箱 + 录播备选 |
| WISE-IoT 免费版有 QPS/存储限制 | 提前确认比赛账号配额；紧急时降级为本地 JSON + Grafana 备选方案 |

---

## 7. 评审维度应对

| 维度 | 得分点 |
|------|--------|
| **技术完整性** | 端-边-云三层 + 5类风险全覆盖 + 多传感器融合 |
| **创新性** | 消防通道全流程闭环 + 边缘隐私保护 + 低成本可复制 |
| **落地价值** | 住建部政策刚需 + 替代80%人工巡查 + 街道平台对接 |
| **生态契合** | 全链路比赛推荐硬件 + 比赛免费平台 |

---

## 8. 团队分工 & 9. 里程碑

- 算法×1 + 嵌入式×1 + 全栈×1 + 文档×1 + PM×1
- 6/15 书审 → 7/14 初赛 → 8/18 决赛 → 9/19 总决赛

## 10. 参考资源

| 资源 | 链接 |
|------|------|
| 大赛官网 | https://aiotinnovation-edu.advantech.com.cn/ |
| 硬件清单 | https://aiotinnovation-edu.advantech.com.cn/Guide/formlist |
| MIC-711D-ON DS | [官方 PDF](https://advdownload.advantech.com.cn/productfile/PIS/MIC-711D-ON/file/MIC-711D-ON_DS(081225)20250813085402.pdf) |
| Gemini 336L | https://www.orbbec.com.cn/index/Product/info.html?cate=38&id=65 |
| Orbbec SDK | https://github.com/orbbec/OrbbecSDK_ROS2 |
| YOLO26 文档 | https://docs.ultralytics.com/models/yolo26 |
| Jetson 基准 | https://docs.ultralytics.com/guides/nvidia-jetson |
| DeepStream 指南 | https://docs.ultralytics.com/guides/deepstream-nvidia-jetson |
| IoTSuite 文档 | https://docs.wise-paas.advantech.com.cn/zh-cn |
