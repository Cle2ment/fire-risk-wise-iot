# WISE-IoT/Dashboard 可视化配置指南

> **项目：基于 AIoT 的城市老旧小区智慧安防与消防通道联动管控系统**
> **赛事：2026 研华全国 AIoT 创新应用大赛**
**生成日期：2026-07-14**
**适用阶段：初赛（Dashboard 搭建 + IoTSuite 设备注册已完成）**

---

## 目录

1. [平台概述](#1-平台概述)
2. [数据流架构](#2-数据流架构)
3. [数据源配置](#3-数据源配置)
4. [DataHub 数据接入](#4-datahub-数据接入)
5. [Panel 设置指南](#5-panel-设置指南)
6. [WISE-PaaS 增强功能](#6-wise-paas-增强功能)
7. [SRP-Frame 应用框架](#7-srp-frame-应用框架)
8. [告警与通知配置](#8-告警与通知配置)
9. [MongoDB 数据源（备选）](#9-mongodb-数据源备选)
10. [项目实施方案](#10-项目实施方案)
11. [参考资源](#11-参考资源)

---

## 1. 平台概述

### 1.1 WISE-IoT/Dashboard 是什么

WISE-IoT/Dashboard 是基于 **Grafana** 的企业级数据可视化平台，在标准 Grafana 之上新增了 **10 大增强功能模块**、**25 支行业显示插件**、**9 支数据源插件**，并内置低代码应用构建框架 **SRP-Frame**。

**核心能力：**

| 能力 | 说明 |
|------|------|
| 零代码可视化 | 拖拽配置即可构建大屏，无需编程 |
| 50+ 数据源 | InfluxDB、PostgreSQL、MongoDB、DataHub、MQTT 等 |
| 70+ 显示面板 | 时序图、统计值、表格、告警面板、视频面板等 |
| 多租户权限 | Org → Folder → Dashboard 三级权限控制 |
| 多端自适应 | 2K/4K/8K 大屏 + PC + 手机 |

### 1.2 与本项目相关的 WISE-IoT 服务

| 服务 | 用途 | 与 Dashboard 的关系 |
|------|------|---------------------|
| **Dashboard** | 数据可视化 | 核心展示层 |
| **DataHub** | MQTT/HTTP/CoAP 数据接入 | 数据源（SimpleJson 插件） |
| **SaaS Composer** | 低代码应用 + 2D/3D 模型 | 嵌入 Dashboard 显示 |
| **Notification** | 微信/短信/邮件告警推送 | Alert 触发后自动推送 |
| **AgentBuilder** | 工业 AI Agent 开发 | 告警处置决策 + LLM 建议 |
| **DataInsight** | BI 分析报表 | 周报/月报自动生成 |

> **评审提示**：全链路使用上述推荐服务可在「生态契合」（25%）维度获得 **+8~10 分**。详见 [§10.4](#104-评审加分)。

---

## 2. 数据流架构

### 2.1 端-边-云数据流

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TB
  subgraph Perception["感知层"]
    A1["Gemini 336L 深度相机<br/>GMSL2.0/USB3.0"]
    A2["WISE-4012E<br/>烟感/温感 → RS-485"]
    A3["WISE-4051<br/>地磁 → DI"]
  end

  subgraph Edge["边缘 AI 层<br/>MIC-711D-ON · Jetson Orin Nano"]
    B1["DeepStream 7.1 视频管线"]
    B2["nvv4l2decoder → nvinfer<br/>YOLO → nvtracker → nvdsosd"]
    B3["MQTT Publisher"]
    B4["ECU-1051E Broker<br/>192.168.1.101:1883"]
  end

  subgraph Cloud["云端 · WISE-IoT"]
    C1["DataHub<br/>多协议数据接入"]
    C2["InfluxDB / PostgreSQL<br/>时序+结构化存储"]
    C3["Dashboard<br/>数据可视化"]
    C4["SaaS Composer<br/>工单联动"]
    C5["Notification<br/>微信/短信推送"]
    C6["AgentBuilder<br/>AI决策"]
  end

  A1 & A2 & A3 --> B1
  B1 --> B2 --> B3
  B3 -->|"MQTT QoS 1"| B4
  B4 -->|"MQTT"| C1
  C1 --> C2
  C2 --> C3
  C3 --> C4
  C3 --> C5
  C3 --> C6
  C5 -->|"告警分派"| C4

  classDef sensor fill:#1a5276,stroke:#0e2f44,color:#d4e6f1
  classDef edge fill:#1e8449,stroke:#145a32,color:#d5f5e3
  classDef cloud fill:#6c3483,stroke:#4a235a,color:#e8daef
  classDef broker fill:#b9770e,stroke:#7d6608,color:#fdebd0
  class A1,A2,A3 sensor
  class B1,B2,B3 edge
  class C1,C2,C3,C4,C5,C6 cloud
  class B4 broker
```

### 2.2 MQTT Topic 结构与 Payload

边缘端通过 ECU-1051E Broker 发布数据，DataHub 订阅后转发至云端：

```
smart_community/{community_id}/
├── alerts/
│   ├── fire_lane_violation     ← 消防通道违停
│   ├── channel_obstruction     ← 通道堆物
│   ├── abnormal_loitering      ← 异常徘徊
│   ├── high_altitude_throwing  ← 高空抛物
│   └── elderly_fall            ← 老人跌倒
├── sensors/
│   ├── smoke_detector/{id}     ← 烟感
│   ├── temperature/{id}        ← 温感
│   └── geomagnetic/{id}        ← 地磁
├── devices/{id}/
│   ├── status                  ← 设备心跳
│   └── telemetry               ← GPU/CPU 指标
└── events/
    ├── alert_resolved/{id}     ← 告警已处置
    └── device_offline/{id}     ← 设备离线
```

**告警 Payload 示例：**

```json
{
  "alert_type": "fire_lane_violation",
  "community_id": "C001",
  "camera_id": "cam_01",
  "timestamp": "2026-07-13T14:30:00+08:00",
  "severity": "high",
  "location": "3栋西侧消防通道",
  "bbox": [120, 340, 480, 620],
  "confidence": 0.92,
  "image_snapshot": "base64_encoded_jpeg",
  "duration_seconds": 45,
  "vehicle_plate": "京A12345"
}
```

---

## 3. 数据源配置

### 3.1 支持的数据源类型

| 类别 | 数据源 | 适用场景 |
|------|--------|----------|
| WISE-PaaS 平台 | DataHub, InsightAPM, DeviceOn, AIFS, IoT Hub | 平台原生数据，无缝对接 |
| 时序数据库 | InfluxDB, Prometheus, Graphite | IoT 时序数据 |
| 关系数据库 | PostgreSQL, MySQL, MS SQL Server | 结构化业务数据 |
| 文档数据库 | MongoDB（通过代理，见 §9） | 半结构化 JSON 数据 |
| 消息队列 | MQTT（通过 DataHub，见 §4） | 设备遥测 |
| 边缘采集 | WebAccess | 工业 SCADA 数据 |

### 3.2 DataHub 数据源配置（主要方式）

本项目告警和传感器数据通过 **DataHub-SimpleJson** 插件接入。

**配置步骤：**

1. Dashboard → Configuration → Data Sources → Add data source
2. Type 选择 `DataHub`（SimpleJson 变体）
3. 配置连接参数：

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| Name | `SmartCommunity-DataHub` | 自定义 |
| URL | `https://portal-datahub-{ns}.{cluster}.wise-paas.com` | **末尾不加 `/`** |
| Access | `direct`（公有云）或 `proxy`（自签） | 见下表 |
| Auth | `With Credentials` | 使用登录用户凭证 |

**Access 模式选择：**

| 模式 | 适用场景 | 额外配置 |
|------|----------|----------|
| direct + With Credentials | 公有云，数据随用户不同 | 无需额外配置 |
| direct + Anonymous | 公开数据，无需登录 | 预设账号（建议 viewer 权限） |
| proxy + With Credentials | 自签私有云 | Skip TLS Verify + Cookies: `EIToken` |
| proxy + Anonymous | 自签 + 公开数据 | 同上 + 预设账号 |

4. 点击 **Save & Test** 验证连接。

### 3.3 其他数据源（备选）

| 数据源 | 关键参数 | 用途 |
|--------|----------|------|
| InfluxDB | URL + Database + User/Password | 直接读时序数据 |
| PostgreSQL | Host:5432 + Database + User/Password | 读业务数据 |
| MySQL | Host:3306 + Database + User/Password | 读业务数据 |

---

## 4. DataHub 数据接入

### 4.1 数据模型

DataHub 采用层级结构组织数据：

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TD
  P["Project<br/>项目/小区<br/>例: SmartCommunity"]
  N["Node<br/>网关/边缘节点<br/>例: MIC-711D-ON-N01"]
  D["Device<br/>设备/传感器<br/>例: cam_01"]
  T["Tag<br/>数据测点<br/>例: violation_count"]

  P --> N --> D --> T

  classDef level fill:#1a5276,stroke:#0e2f44,color:#d4e6f1
  class P,N,D,T level
```

Dashboard 查询时按此层级逐级选择：**Project → Node → Device → Tag**。

### 4.2 MQTT 接入配置

1. 登录 WISE-IoT 控制台 → DataHub
2. 创建 **Node**（对应 MIC-711D-ON 边缘节点）
3. 创建 **Device**（对应每个传感器/摄像头）
4. 获取 **Node ID + Credential Key**（MQTT 连接凭证）
5. 配置数据接入规则：
   - 协议：MQTT
   - Broker：`192.168.1.101:1883`（ECU-1051E）
   - 订阅 Topic：`smart_community/+/alerts/#`、`smart_community/+/sensors/#`
6. 配置数据转发规则 → InfluxDB（时序）/ PostgreSQL（结构化）
7. 创建 Schema 映射（JSON 字段 → 数据库列）

**EdgeLink MQTT 参考参数：**

| 参数 | 本项目值 |
|------|----------|
| Connection Type | MQTT 3.1.1 |
| Host:Port | `192.168.1.101:1883` |
| Node ID / Credential Key | DataHub 创建 Node 后生成 |
| Keep Alive | 60s |
| Upload Interval | 5s |

### 4.3 Dashboard 查询 DataHub 数据

Panel 编辑器中：选择 DataHub 数据源 → Project → Node → Device → Tag → 选择 Timeserie/Table → 设置聚合方式。

**示例查询：**
```
Tag: fire_lane_violation_count
Aggregation: count
Group By: time(1m)
```

---

## 5. Panel 设置指南

### 5.1 Panel 类型速查

| Panel | 用途 | 本项目场景 |
|-------|------|-----------|
| **Graph** | 折线图/柱状图 | 告警趋势、传感器时序 |
| **Singlestat** | 单值 KPI | 今日告警总数、设备在线率 |
| **Table** | 数据表格 | 告警记录、设备清单 |
| **Gauge / Bar Gauge** | 仪表盘 | CPU/GPU 使用率、温度 |
| **Pie Chart** | 饼图/环形图 | 告警类型分布 |
| **Stat** | 统计面板 | KPI 指标卡 |
| **Heatmap** | 热力图 | 告警时段分布 |
| **Alert List** | 告警列表 | 实时告警滚动 |
| **Dash Video** | 视频播放 | 摄像头 RTMP/HLS 画面 |
| **Worldmap Panel** | 地图标注 | 小区地图 + 设备位置 |
| **Diagram** | 流程图 | 消防通道示意图 |
| **Text/HTML** | 富文本 | 大屏标题 |

### 5.2 Graph Panel 配置要点

| 区域 | 关键设置 | 建议值 |
|------|----------|--------|
| Metrics | 数据源 + Tag | DataHub，选择告警 Topic |
| Legend | 图例显示 | Show + avg/max/min |
| Axes | Y 轴 | 自动或固定范围 |
| Display | 样式 | Lines + Points, 线宽 2px |
| Alert | 告警条件 | 见 §8 |

**WISE-PaaS 增强：** 支持算式计算、统计控制线 UCL/CL/LCL、离散统计、按天聚合。

### 5.3 Singlestat Panel 配置要点

| 参数 | 推荐设置 |
|------|----------|
| Value → Stat | Current / Avg / Max / Total |
| Value → Unit | 次、%、℃ |
| Value → Decimals | 0-2 |
| Coloring → Thresholds | 0-50 绿, 50-100 黄, 100+ 红 |
| Spark lines | 开启迷你趋势图 |

### 5.4 Table Panel 配置要点

| 参数 | 设置 |
|------|------|
| Columns | 选择要显示的列 |
| Column Styles | 日期格式、数值精度、颜色阈值 |
| Row Coloring | 按状态列着色 |

### 5.5 Dash Video Panel

支持 RTMP / HLS / DASH 多协议，含历史回放和子码流。

配置：DeepStream 输出 RTMP 流 → Dashboard 添加 Dash Video Panel → 输入视频流 URL。

### 5.6 通用技巧

- **布局**：拖拽 Panel + Row 分组 + 变量动态切换
- **刷新**：全局 5s-5m 间隔，单个 Panel 可覆盖
- **大屏**：使用 Title Panel + 背景色/图 + 边框样式（见 §6.1）

---

## 6. WISE-PaaS 增强功能

### 6.1 显示美化

| 增强项 | 配置路径 |
|--------|----------|
| 背景色/图 | Dashboard Settings → General |
| 边框样式 | Panel → Display（3 种内置 + 自定义） |
| Panel Title | 10 种默认样式 + 颜色阴影 |
| 大屏 Title Panel | 多种内置样式 |

### 6.2 变量增强

1. **变量 Panel**：变量下拉框可放置在 Dashboard 任意位置
2. **依赖变量**：级联选择（小区 → 楼栋 → 摄像头），支持 text/id 双模式

```
变量1: 小区 (community_id) → C001, C002, C003
变量2: 摄像头 (camera_id) → 依赖变量1 → 动态选项
变量3: 告警类型 (alert_type) → 违停/堆物/徘徊/抛物/跌倒
```

### 6.3 其他增强

| 功能 | 说明 |
|------|------|
| **图片管理** | 内置图片服务器，bmp/jpg/png/gif/svg，Infographic/PictureIt 直接使用 |
| **多分辨率** | 2K/4K/8K 大屏 + PC + 手机自适应 |
| **多语言** | Dashboard + DataSource + SRP-Frame 多语言配置 |
| **SSO** | WISE-PaaS 平台角色自动登录 |
| **批量导入导出** | Org 级 Dashboard + 数据源 + SRP-Frame zip 打包 |

---

## 7. SRP-Frame 应用框架

### 7.1 简介

SRP-Frame 将多个 Dashboard 组织为带目录导航的应用。**核心功能：**

- 自定义左侧菜单树（多级 + 图标）
- Logo 更换 + 跑马灯
- 红色铃铛（告警事件）+ 黄色铃铛（通知事件）
- 支持 API/WebSocket 接入
- 三屏战情室（左中右，左右轮播，中间互动）
- 单屏 55" 模式：URL 后加 `?layout=ss`

### 7.2 本项目菜单结构

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TD
  ROOT["智慧社区安防管控平台"]

  CAT1["总览大屏"]
  CAT2["消防通道管控"]
  CAT3["人员安全"]
  CAT4["环境监测"]
  CAT5["工单管理"]
  CAT6["设备运维"]

  A1["今日告警看板"]
  A2["设备运行状态"]
  B1["违停实时监控"]
  B2["通道堆物检测"]
  C1["异常徘徊检测"]
  C2["高空抛物监控"]
  C3["老人跌倒告警"]
  D1["烟感数据"]
  D2["温感数据"]
  D3["地磁数据"]
  E1["告警处置记录"]
  E2["巡检工单"]
  F1["边缘设备状态"]
  F2["摄像头在线状态"]

  ROOT --> CAT1 & CAT2 & CAT3 & CAT4 & CAT5 & CAT6
  CAT1 --> A1 & A2
  CAT2 --> B1 & B2
  CAT3 --> C1 & C2 & C3
  CAT4 --> D1 & D2 & D3
  CAT5 --> E1 & E2
  CAT6 --> F1 & F2

  classDef root fill:#1a5276,stroke:#0e2f44,color:#d4e6f1
  classDef cat fill:#1e8449,stroke:#145a32,color:#d5f5e3
  classDef item fill:#4a235a,stroke:#2e1444,color:#e8daef
  class ROOT root
  class CAT1,CAT2,CAT3,CAT4,CAT5,CAT6 cat
  class A1,A2,B1,B2,C1,C2,C3,D1,D2,D3,E1,E2,F1,F2 item
```

---

## 8. 告警与通知配置

### 8.1 Dashboard Alert Rule

在 Graph / Singlestat Panel → Alert 选项卡中配置：

| 参数 | 说明 | 示例 |
|------|------|------|
| Name | 告警名称 | `消防通道违停告警` |
| Evaluate every | 评估间隔 | `1m` |
| For | 持续触发阈值 | `2m`（避免误报） |
| Conditions | 触发条件 | `WHEN avg() OF query(A, 5m, now) IS ABOVE 1` |
| No Data | 无数据处理 | `Keep Last State` |

### 8.2 Notification 渠道

| 渠道 | 配置方式 |
|------|----------|
| **微信** | Notification 服务绑定企业微信/个人微信 |
| **短信** | 配置短信网关 |
| **邮件** | SMTP 服务器 |
| **DingTalk** | Webhook URL |
| **Webhook** | 自定义 HTTP 回调（对接街道平台） |
| Slack / LINE / Telegram | 标准集成 |

**告警分派策略：**
- 违停/堆物 → 物业保安（微信 + 短信）
- 高空抛物/跌倒 → 紧急响应组（全渠道）
- 烟感告警 → 消防值班（全渠道）

### 8.3 SaaS Composer 自动化工单

Alert 触发 → SaaS Composer 规则引擎 → 自动生成工单（违停派保安 / 跌倒紧急响应）→ 状态回流 Dashboard。

---

## 9. MongoDB 数据源（备选）

如 DataHub 默认存储不满足需求，可部署 MongoDB 代理直接存储告警记录。

### 9.1 架构

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart LR
  subgraph Browser["浏览器"]
    G["Grafana Panel<br/>MongoDB 查询"]
  end

  subgraph Proxy["Node.js Proxy :3000"]
    P1["POST /query<br/>时序/表格数据"]
    P2["POST /search<br/>模板变量"]
    P3["POST /<br/>连接测试"]
  end

  subgraph DB["MongoDB"]
    M["db.alerts<br/>告警记录集合"]
  end

  G -->|"HTTP POST<br/>聚合查询"| Proxy
  P1 & P2 & P3 -->|"aggregate()"| M
  M -->|"{name, value, ts}<br/>表格行/列"| Proxy
  Proxy -->|"Grafana API<br/>Timeseries/Table"| G

  classDef panel fill:#1a5276,stroke:#0e2f44,color:#d4e6f1
  classDef proxy fill:#1e8449,stroke:#145a32,color:#d5f5e3
  classDef db fill:#6c3483,stroke:#4a235a,color:#e8daef
  class G panel
  class P1,P2,P3 proxy
  class M db
```

### 9.2 部署步骤

```bash
# 1. 构建镜像
cd vendor/dashboard-mongo-datasource-example
docker build -t {account}/mongodb:api .
docker push {account}/mongodb:api

# 2. 在 Portal-Service 创建 MongoDB Secret
# 3. 修改 k8s/server.yaml + k8s/ingress.yaml（替换 account、secret、host）
# 4. 部署
kubectl apply -f k8s/
```

**Dashboard 数据源配置：**

| 参数 | 值 |
|------|-----|
| Type | MongoDB |
| URL | `http://dashboard-mongodb-api.{space}.eks004.en.internal` |
| MongoDB URL | `mongodb://user:pass@host:27017/dbname` |

### 9.3 查询语法

```javascript
// 时序（Graph Panel）
db.alerts.aggregate([
  { $match: { ts: { $gte: '$from', $lt: '$to' }, alert_type: 'fire_lane_violation' } }
])
// 返回字段：{ name, value, ts }

// 表格（Table Panel）
db.alerts.aggregate([
  { $match: { ts: { $gte: '$from', $lt: '$to' } } },
  { $sort: { ts: -1 } },
  { $limit: 100 }
])
```

**内置变量：** `$from` / `$to`（BSON 日期），`$dateBucketCount`（桶数量）。

---

## 10. 项目实施方案

### 10.1 决赛阶段任务（5 天）

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1-2 | Dashboard 搭建 | 5 个监控面板，拖拽布局，DataHub 数据源验证 |
| Day 3 | DataHub 接入 | MQTT Topic 注册 + 转发规则 + Schema 映射 |
| Day 4 | 联动配置 | SaaS Composer 工单规则 + Notification 推送 + AgentBuilder |
| Day 5 | 美化与测试 | 大屏适配 + 全链路压力测试 |

### 10.2 Dashboard 规划

| Dashboard | 核心 Panel | 数据源 |
|-----------|-----------|--------|
| 总览看板 | Singlestat + Graph + Pie Chart | DataHub |
| 消防通道监控 | Graph + Table + Dash Video | DataHub |
| 人员安全监控 | Singlestat + Table | DataHub |
| 环境监测 | Gauge + Graph | DataHub |
| 设备运维 | Stat + Table | DataHub |

### 10.3 配置检查清单

- [ ] DataHub MQTT 数据源创建并验证连接
- [ ] 5 类告警 Topic 在 DataHub 注册
- [ ] JSON Payload Schema 映射配置
- [ ] 主 Dashboard 创建（≥6 个 Panel）
- [ ] Alert Rule 配置（5 类各一条）
- [ ] Notification 渠道绑定（微信 + 短信）
- [ ] SaaS Composer 工单模板
- [ ] SRP-Frame 菜单结构
- [ ] 大屏 2K/4K 适配测试
- [ ] 刷新间隔设置（建议 5s）

### 10.4 评审加分

「生态契合」（25%）维度，全链路使用推荐服务可获 **+8~10 分**：

| 服务 | 状态 | 加分 |
|------|------|------|
| Dashboard | ✅ 核心 | +2 |
| DataHub | ✅ 核心 | +2 |
| SaaS Composer | ✅ 推荐 | +1 |
| Notification | ✅ 推荐 | +1 |
| AgentBuilder | ✅ 推荐 | +1.5 |
| DataInsight | ✅ 决赛 | +1.5 |
| 全部推荐硬件 | ✅ 计划中 | +1 |

---

## 11. 参考资源

### 官方文档

| 资源 | 链接 |
|------|------|
| **DataHub → Dashboard Quick Start**（官方教程） | https://docs.wise-paas.advantech.com/en/Guides_and_API_References/Industrial_IoT_Cloud_Platform/Quick_Start_Guide/1595243156540582666/v3.0.0 |
| WISE-IoT 技术文档中心 | https://docs.wise-paas.advantech.com/zh-cn |
| Dashboard 产品简介 | https://docs.wise-paas.advantech.com/zh-cn/Guides_and_API_References/ApplicationServices/Dashboard/1605799235152848843/v1.0.1 |
| Dashboard 加值说明（完整版） | https://docs.wise-paas.advantech.com/zh-cn/Guides_and_API_References/ApplicationServices/Dashboard/1607652728231511964/v3.0.21 |
| EdgeLink → DataHub MQTT 指南 | https://learn.advantech.com/EdgeLink/Cloud/WISE-PaaS/ |
| Dashboard 在线 Demo | https://dashboard-dashboard-eks001.hz.wisepaas.com.cn/frame/caseSet（需内网/VPN 访问） |
| WISE-PaaS 技术论坛 | https://forum.wise-paas.advantech.com/ |
| Grafana 官方文档 | https://grafana.com/docs/ |

### WISE-PaaS GitHub 示例仓库

全部位于 https://github.com/WISE-PaaS/ 组织：

| 仓库 | 说明 |
|------|------|
| dashboard-mongo-datasource-example | MongoDB 数据源代理插件（Node.js, K8s） |
| dashboard-plugin-sample | Dashboard 插件开发示例（JavaScript） |
| example-py-iothub-mongodb-dashboard | MQTT + MongoDB + Dashboard（Python） |
| example-py-iothub-postgresql-dashboard | MQTT + PostgreSQL + Dashboard（Python） |
| simple-json-datasource | SimpleJSON 数据源参考实现 |

### 本地文档

| 文件 | 路径 |
|------|------|
| Dashboard 加值说明（PDF, 58 页） | `vendor/wise-iot-docs/WISE-IoT-Dashboard-基于Grafana的加值说明.pdf` |
| Dashboard 加值说明（Markdown） | `vendor/wise-iot-docs/WISE-IoT-Dashboard-基于Grafana的加值说明/` |
| MongoDB 数据源示例（完整代码） | `vendor/dashboard-mongo-datasource-example/` |
| 项目路线图 | `documentation/ROADMAP.md` |
| 项目技术方案 | `documentation/DESCRIPTION.md` |

### 示例 Dashboard 文件

| 文件 | 用途 |
|------|------|
| `examples/mongodb_demo.json` | Graph + Table 面板示例 |
| `k8s/` | K8s Deployment + Service + Ingress |
| `server/mongodb-proxy.js` | MongoDB → Grafana API 代理 |

> **维护说明**：本文档基于 2026-07-13 可获取的最新资料编写。WISE-IoT 平台持续更新，具体操作以平台最新界面为准。如有配置问题，请查阅官方技术论坛或联系研华技术支持。
