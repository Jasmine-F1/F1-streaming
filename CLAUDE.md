# CLAUDE.md

本文件用于让 Claude Code(VS Code 内)理解这个项目的目标、架构和关键决策，避免每次开新会话都要重新解释背景。

## 项目目标

**F1 Real-Time Data Platform** — 一个用于求职 Portfolio 的项目，目标岗位是 Williams F1 Racing 的
**Platform Engineer**（Grove, Wantage）。这个项目的核心是**平台工程能力**（Kubernetes / Terraform /
Helm / CI-CD / GitOps / Observability），F1 遥测数据管道只是跑在这个平台上的示例应用负载，
不是项目的重点。

### 候选人背景
- 现职：Data Engineer，医疗保险 payment integrity 领域，技术栈 GCP、Airflow、Jenkins、Python、SQL
- 已有 Claude 相关经验：Claude-based 部署自动化、Claude session hook 集成 Confluence 知识库、
  RAG pipeline（这些经验和目标 JD 里的 "Claude Code skills / MCP server integrations" 直接相关）
- 缺口：Kubernetes、Terraform、Helm、GitOps、Prometheus/Grafana 这套平台工程栈基本零经验，
  这个项目就是用来补这块的

### 目标 JD 要点（Williams F1 Platform Engineer）
- **Essential**：Kubernetes 部署运维（EKS / on-prem / AKS）、Terraform + Helm 做 IaC、
  Docker + Operators、AWS/Azure、CI/CD（GitHub Actions / Bitbucket Pipelines）、
  GitOps（ArgoCD）、Prometheus/Grafana/Loki 监控告警、Python/Bash 脚本
- **Beneficial**：多云/混合云、云原生安全、SLO/SLI/error budget、事故响应、
  **Claude Code / GitHub Copilot 等 AI 辅助开发工具**、开发者体验工具/CLI、
  面向非技术用户的 self-service 工作流

> 注：另有一个更偏数据分析方向的项目想法（用 FastF1 数据做轮胎衰减建模/进站策略模拟），
> 那个是给 Race Strategy / Data Scientist 类岗位用的，跟这个项目是两个不同方向，不要混在一起做。

## 架构

**应用层（数据管道）**：

```
Telemetry Generator → Kafka → Faust 流处理 → 校验 + 特征工程
                                                    ├─→ Prometheus Alertmanager（告警）
                                                    ├─→ Grafana（mission control 看板）
                                                    └─→ Claude MCP Copilot（自然语言查询）
```

**平台层（负责部署和运维应用层）**：

```
Terraform（VPC / EKS / IAM）
   → Kubernetes 集群（本地用 kind，最终演示用真实 AWS EKS）
      → Helm charts（打包每个管道服务）
         → GitHub Actions CI/CD（build → test → push image）
            → ArgoCD（GitOps 自动同步部署）
               → Prometheus / Grafana / Loki（可观测性）
```

## 关键技术决策（不要偏离，除非明确讨论过再改）

1. **不用 Flink，用 Faust（Python）做流处理** —— 为了把时间省下来花在平台工程层。
   Faust 概念上和 Kafka Streams/Flink 相通，以后要升级到真 Flink 是渐进式的，不是推倒重来。
2. **不自己写 alert engine，直接用 Prometheus + Alertmanager** 定义业务指标告警规则
   （比如数据延迟、异常遥测值）——这直接对应 JD 里的 monitoring/alerting 要求。
3. **不自己写前端 dashboard，直接用 Grafana** 做 "mission control" 风格的实时看板。
4. **AI copilot 就是一个 Claude Code skill / MCP server**，能用自然语言查询管道健康状况、
   最近的告警、Faust 消费延迟等——这是 JD 里明确点名、且和候选人现有 Claude 自动化经验
   直接衔接的差异化亮点。
5. **Kubernetes 集群策略**：日常开发全部用本地 `kind` 集群（零成本）。Terraform 代码要同时
   支持 `kind` provider 和真实 AWS，用变量/workspace 切换。最后收尾阶段跑一次真实 AWS EKS
   部署做验证和录屏留证据，然后立刻 `terraform destroy` 避免持续产生费用。
6. **CI 用 GitHub Actions**（免费额度对个人项目足够）。

## 时间线（1-2 周 MVP，之后可再迭代加深）

**第 1 周：管道骨架 + 基础平台**
- Day 1-2：Telemetry generator（可以用 OpenF1 真实比赛数据回放增加真实感）+ Kafka
  （用 Bitnami Helm chart 部署，不自己搭）
- Day 3-4：Faust 流处理服务（消费 Kafka → 校验 → 特征工程），Dockerize
- Day 5-7：Terraform 搭基础云资源 + Helm chart 把所有服务部署到本地 kind 集群 +
  GitHub Actions CI/CD 打通

**第 2 周：可观测性 + 差异化亮点**
- Day 8-9：ArgoCD GitOps 接入；Prometheus 抓取管道指标 + Alertmanager 告警规则
- Day 10-11：Grafana 看板
- Day 12-13：Claude Code skill / MCP server（自然语言查询平台状态）
- Day 14：README + 架构图 + 设计决策文档，整理成 portfolio case study；
  跑一次真实 AWS EKS 部署验证，录屏/截图存档后 destroy

## 给 Claude Code 的协作约定

- 代码注释、commit message、README 用英文；跟我日常对话可以用中文。
- 优先级原则：如果在"管道业务逻辑复杂度"和"平台工程实操深度"之间要做取舍，
  **优先选择能展示 K8s / Terraform / Helm / CI-CD / GitOps / Observability 技能的方案**，
  管道本身做到"够用、能跑通"即可，不需要过度打磨。
- 每完成一个阶段性模块，在 `docs/progress-log.md` 里追加记录（做了什么、为什么这么选、怎么验证的）；
  README.md 只保留当前架构快照和高层进度勾选表，细节都进 progress-log，不要堆在 README 里。
- **任何会产生真实云费用的操作（创建/销毁 EKS 集群等）必须先跟我确认，不要自动执行。**
