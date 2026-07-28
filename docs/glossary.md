# 平台概念术语表

这份文档记录 kind / Kubernetes / Helm / Kafka / Faust / Prometheus / Terraform /
Spark 各自是什么、怎么工作、以及它们之间的关系——写给自己以后不确定的时候回来查。
跟 [architecture.md](architecture.md)（讲这个项目的架构）和
[progress-log.md](progress-log.md)（讲每一步做了什么）不是一回事，这份是纯概念/
术语参考。

## 全局图景：四者怎么串起来

```
kind          → 造出一个"假的但真实可用"的 K8s 集群（本地几个 Docker 容器扮演节点）
                一次性，粒度最粗：造一整个数据中心
   ↓
Helm          → 把 Bitnami 写好的 Kafka chart，按我们的 values.yaml 参数，
                提交给这个集群（相当于施工队按图纸在地皮上盖一栋楼）
                一次性（除非改配置才 upgrade），粒度中等：盖一个仓库
   ↓
Kubernetes    → 实际把 Helm 提交的 YAML（Pod/Service/PVC）调度、运行、
                并持续维持这些资源存活（Pod 崩了自动重启）
                持续运行，不是一次性的
   ↓
Kafka         → 跑在 K8s 管理的 Pod 里，真正接收 telemetry-generator 发来的
                消息，按 offset 顺序持久化存储
                运行时行为，每次发消息都会用到，跟 kind/Helm 完全无关
```

**关键认知**：这四层的"变动频率"完全不同——kind 几乎不变，Helm 偶尔变（改配置/装新组件才变），
Kubernetes 持续在后台自愈，Kafka 里的数据每次运行 pipeline 都在变。不要把它们混成一件事。

---

## Kubernetes (K8s)

**是什么**：一个容器编排系统。你告诉它"我要的最终状态是什么样"（比如"要有 1 个 Kafka pod
一直运行"），它自己想办法达成并**持续维持**这个状态——这是**声明式模型**，跟 Terraform 的
哲学一致。

**核心概念**：
- **Node**：一台机器（物理机/虚拟机/容器），集群由多个 node 组成
- **Pod**：K8s 里最小的部署单位，包一个或多个容器
- **Control plane**：集群的"大脑"，负责调度决策、维护集群状态
- **自愈能力**：Pod 崩了，K8s 自动重启，维持你设定的副本数——全程自动，不需要人工干预，
  也不经过 Helm

---

## kind ("Kubernetes IN Docker")

**是什么**：一个工具，用 Docker 容器去模拟 K8s 的"节点"，从而在本地笔记本上跑一个
**真实、完整的 K8s 集群**，不需要连云、不花钱。

**怎么理解**：相当于在电脑里用 Docker 造出一块"地皮"（K8s 集群），`kubectl` 用起来
和操作真实 AWS EKS 集群完全一样——因为 kind 和 EKS 对外暴露的是同一套 K8s API。这也是
为什么本项目"日常开发用 kind，最后收尾跑一次真 EKS"代码/配置几乎不用改。

**关键点**：kind 造出来的集群是**通用的、空的**，它完全不知道 Kafka 是什么，更不知道
以后会有 `f1.telemetry` 这个 topic。kind 只负责"地基"这一层。

**本项目命令**：`kind create cluster --config infra/kind/kind-config.yaml`
（封装在 `scripts/setup-local-cluster.sh` 里）

---

## Helm

**是什么**：K8s 的包管理器，类比 `apt install` / `pip install`，只不过装的是"一组 K8s
资源配置"（Deployment、Service、PVC、ConfigMap 等一堆 YAML）。

**怎么工作（实际机制）**：
```
Chart（模板，带占位符）+ values.yaml（你填的参数）
        ↓  Helm 把两者渲染合并
最终的 K8s YAML manifest（具体的 Deployment/Service/PVC 定义）
        ↓  Helm 把这些 YAML 提交给 K8s API Server
K8s 接收后，自己去创建资源、调度 Pod（真正"施工"的是 K8s，不是 Helm）
```

**核心概念**：
- **Chart**：一份打包好的、模板化的 K8s 配置集合（比如 Bitnami 维护的 `kafka` chart）
- **Values**：chart 的参数化配置（本项目：`infra/helm/kafka-values.yaml`）
- **Release**：一次 `helm install`/`upgrade` 产生的、有版本号的部署实例

**怎么理解**：Helm 更像一支**可重复使用的施工队**，不是仓库本身——你给它一份图纸
（chart），它就去按图纸盖一栋楼。盖 Kafka 是一个项目，以后盖 Grafana 是另一个项目，
用的是**同一支施工队**（Helm 这个工具只装一次），只是每次拿不同图纸。真正的"仓库"
是 Kafka 部署本身（施工队盖出来的 Pod/Service/存储卷），不是 Helm。

**Helm 需要 K8s 吗**：绝对需要，硬依赖。Helm 本质是"跟 K8s API 对话的客户端"，没有
一个正在运行的 K8s 集群，`helm install` 直接报错连不上。Helm 通过读取 `~/.kube/config`
（`kubectl` 也读同一个文件）知道该往哪个集群发指令。**所以必须先有 kind 集群，才能跑
Helm。**

**Helm 是一次性的吗**：装 Kafka 这个动作是一次性的（除非你改配置才需要 `helm upgrade`）。
但装完之后，**日常"往 Kafka 里发数据"完全不经过 Helm**——数据直接走网络连到已经在
运行的 Kafka Pod，Helm 早就退出了，感知不到、也不参与。

**本项目命令**：
```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install kafka bitnami/kafka --version 32.4.3 -n pipeline -f infra/helm/kafka-values.yaml
```

---

## Kafka

**是什么**：一个分布式、持久化、有序的**消息日志系统**。核心定位是"系统之间的实时数据
传送带"，不是数据库，也不是文件存储。

**核心概念**：
- **Topic**：一个逻辑上的数据流分类（本项目：`f1.telemetry`）。类比：一张只能追加
  写入（append-only）的表
- **Partition**：一个 topic 可以切成多个 partition 并行处理，每个 partition 内部
  消息严格有序（本项目目前只有 1 个 partition，自动创建）
- **Offset**：每条消息在 partition 里的位置编号，从 0 开始单调递增，写入后不可修改
- **Producer / Consumer**：写数据的叫 producer（我们的 `telemetry-generator`），
  读数据的叫 consumer（以后的 `faust-processor`）
- **CreateTime**：Kafka 给每条消息记的时间戳，默认 = producer 发送这条消息的时间
  （不是"处理时间"，Kafka 自己不做任何计算，只是单纯记录）
- **Consumer Group / 消费进度**：每个 consumer（或 consumer group）自己维护一个
  "读到哪个 offset 了"的进度指针，存在 Kafka 里。**消息被读取后不会被删除**——
  这意味着同一份数据可以被多个完全独立的下游系统各自读一遍，互不干扰

**Topic 是 K8s 资源吗**：不是。`f1.telemetry` 这个 topic 完全是 Kafka 软件内部的
概念，是 `telemetry-generator` 第一次往这个名字发消息时，Kafka **自动创建**的——
不需要 kind 或 Helm 参与，就是在已有的存储卷里，Kafka 自己开了一个新的日志文件。

### Kafka 跟其他存储的区别

| 对比对象 | 区别 |
| --- | --- |
| 数据库（PostgreSQL/BigQuery） | 数据库为随机访问设计，可以 UPDATE/DELETE/按条件查询；Kafka 只能追加写入，不可修改，没有 SQL/JOIN，不是查询引擎 |
| 对象存储（GCS/S3） | GCS 按路径查找离散文件，无顺序流概念，偏批处理；Kafka 为持续、低延迟、高吞吐的流式写入/读取设计，partition 内严格保序 |
| 传统消息队列（RabbitMQ/SQS） | 传统 MQ 消息被消费后即删除（destructive read）；Kafka 消息读完不删，按保留期过期，支持多个独立下游重复消费同一份数据 |

### Kafka 是常驻服务：空闲时的资源消耗 & 数据保留期

**为什么没有新数据也一直在跑**：Kafka 不是一次性脚本，是一个 **JVM 常驻服务进程**。
这对应 K8s 里的 **StatefulSet/Deployment**（vs. 一次性的 Job/Pod）——Helm 装 Kafka 时
提交的是 StatefulSet（本项目里报错信息 `StatefulSet/pipeline/kafka-controller` 就是
证据），K8s 对它的理解是"我要的最终状态是——永远有 1 个副本在跑"，会**持续维持**这个
状态，不管有没有业务数据流过。这跟 `telemetry-generator`（一次性 Job，跑完就退出、
零占用）是完全不同的两类工作负载。类比：跟你机器上一直在跑的 `postgres`/`mongodb`
一样，数据库服务器不查询的时候也在后台监听端口待命。

**即使空闲，仍然消耗的资源**（本项目实测，`docker stats` 抓的是 kafka pod 所在
worker 节点，包含少量 K8s 系统开销）：
- **内存**：跑 kafka pod 的节点约 ~960MB（JVM 堆 + 线程池等常驻开销）
- **CPU**：约 ~5%，不是完全零——KRaft 一致性协议心跳、日志段检查、指标上报这些
  后台任务持续在跑
- **磁盘**：已写入的消息一直占空间，直到保留期过期
- **K8s 探测流量**：`livenessProbe`/`readinessProbe` 默认每 10 秒探测一次，永久存在
  的背景噪音

**什么时候会真正停止**（只有主动改变"期望状态"才会）：
- `helm uninstall kafka` —— 告诉 K8s 不再需要这个 StatefulSet
- `kind delete cluster`（`scripts/teardown-local-cluster.sh`）—— 整个地基拆除
- Docker Desktop 退出/电脑关机 —— 底层节点容器本身没了
- **不会**因为"没有新数据"而自动停止，这是设计使然，不是异常

**数据保留期（retention）**：Kafka 按**时间**过期数据，不是按"有没有被消费"过期——
消息读完依然留着，直到超过保留期才被清理。本项目用的是 Kafka 默认值，没有覆盖：
```
log.retention.hours = 168        # 7 天，默认值（DEFAULT_CONFIG，未被覆盖）
log.retention.check.interval.ms = 300000   # 每 5 分钟检查一次哪些日志段该删了
log.retention.bytes = -1         # 不按大小限制，只按时间
```
（用 `kafka-configs.sh --entity-type brokers --entity-name 0 --describe --all` 在
broker 上验证过。）也就是说，我们发进去的消息会在写入后 **7 天**自动被清掉，除非
手动改这个配置或者删掉整个 topic。

**⚠️ 对应到真实云成本的启示**：本地 kind 空跑，代价最多是笔记本 CPU/电量；但如果这
套东西部署到真实 AWS EKS，Kafka 这种常驻服务哪怕一条消息都不处理，**这些资源也在
按小时计费**——这正是 CLAUDE.md 里"任何产生真实云费用的操作必须先确认"这条规矩的
由来：EKS 只临时起来验证一次、留证据，然后立刻 `terraform destroy`，绝不空跑攒费用。

### GCP 产品对标

| Kafka 概念 | GCP 对应产品 | 备注 |
| --- | --- | --- |
| Kafka 本身（消息传输骨干） | **Pub/Sub** | 最接近的对标，但不是 1:1——Pub/Sub 全托管 serverless，运维成本低，但分区/顺序控制粒度不如 Kafka 细 |
| 自建/托管 Kafka | **Google Cloud Managed Service for Apache Kafka** | GCP 2024 上线的托管 Kafka，跟我们用的是同一套东西 |
| Faust 这一层（流处理） | **Dataflow**（Apache Beam） | 概念上对应 Kafka Streams/Faust 这类"消费+计算"角色 |
| BigQuery / GCS | 不对应 | 这些是查询/归档层，是 Kafka 数据流的下游终点，不是替代品 |

**为什么这个项目选 Kafka 而不是 Pub/Sub**：目标 JD（Williams F1 Platform Engineer）
提的是 AWS/Azure，不是 GCP。Pub/Sub 是 GCP 专属；Kafka 是跨云、行业标准的事件流技术，
简历信号价值更高。

**跟 Airflow 的范式区别**：Airflow 编排的是批处理 DAG（定时跑一次、跑完结束）；
Kafka 是持续不断的流（没有"跑完"这个概念）。两种完全不同的范式，解决不同的问题。

---

## Faust

**是什么**：一个 Python 流处理框架，设计上模仿 Kafka Streams（Kafka 官方给
Java/Scala 用的流处理库）。用装饰器 `@app.agent()` 写一个"agent"——一个持续运行的
异步函数，声明式地表达"持续消费某个 topic，对每条消息做处理"。本项目用的是
`faust-streaming`（社区维护的 fork），不是原始 `faust` 包（已停止维护）。

**为什么用它**：
- 不自己写原始 consumer 循环——那样得自己管 consumer group、自己实现"记住上一条
  消息"这种状态、自己做容错。Faust 把这些都封装好了
- **vs Flink**：Flink 是 JVM，需要独立集群（JobManager/TaskManager）+ checkpoint
  基础设施，运维成本高；Faust 纯 Python、单进程，能直接当一个普通 K8s 服务部署——
  跟 [CLAUDE.md](../CLAUDE.md) 决策 1"不用 Flink 用 Faust，把时间留给平台工程层"
  完全对应

**核心组件**（对应 `apps/faust-processor/src/app.py`）：
- **Agent**：`@app.agent(topic)` 装饰的函数，持续消费 topic，处理完可以 `.send()`
  到另一个 topic（本项目：读 `f1.telemetry`，写 `f1.telemetry.processed`）
- **Table**：`app.Table(...)`，有状态的键值存储，见下面"Topic vs Table"
- **内建 Web 层**：Faust 自带一个 aiohttp web server（默认端口 6066），用
  `@app.page(...)` 挂路由——本项目用它暴露 `/metrics` 给 Prometheus 抓取，不用
  额外起第二个 HTTP server

### Kafka Topic vs Faust Table：两种容易混淆的东西

`f1.telemetry.processed` 是什么类型？答案：**跟 `f1.telemetry` 是同一种东西——一个
Kafka topic**，不是"dataset"也不是"table"。Faust（和 Kafka Streams 一样）其实同时有
两种不同的数据抽象，本项目代码里刚好两种都用到了：

| | **Topic**（`f1.telemetry`、`f1.telemetry.processed`） | **Table**（`last_speed_kph`、`max_session_time_s`） |
| --- | --- | --- |
| 本质 | 无边界的事件流，只能追加，按顺序存 | 键值存储（类似 dict），每个 key 只保留最新一个值 |
| 存的是什么 | 每一条历史事件都保留 | 每个 driver_number 对应"目前最新的车速/最大 session_time" |
| 能不能按 key 查当前值 | 不能，只能按顺序读 | 能，`table[driver_number]` 直接查 |
| 底层实现 | 就是原生 Kafka topic | 内部靠专门的 Kafka "changelog" topic 做容错（本项目自动建的
  `f1-faust-processor-last-speed-kph-changelog` 就是这个），但对外是键值接口，不是"流" |

**结论**：`f1.telemetry.processed` 和 `f1.telemetry` 是同一类东西（都是 topic/事件
流），只是内容不同。真正的"table"是 faust-processor 内部那两个状态存储——但这是
**内部实现细节**，Grafana、以后的 MCP copilot 都看不到、也不会直接查它们。

---

## Prometheus

**是什么**：一个开源的指标监控/告警系统，核心是它自己的**时间序列数据库**（存
"某个指标在某个时间点的值"）。

**核心机制——主动拉取（pull），不是被推送（push）**：跟很多"服务主动上报数据"的
监控系统不同，Prometheus 是**周期性地主动去请求**每个服务的 `/metrics` HTTP 端点
（比如每 15 秒一次），把返回的文本格式指标解析后存起来。这就是为什么
faust-processor 要专门开一个 `/metrics` 页面——它是留给 Prometheus 来"拉"的接口，
不是给人看的，Grafana 也不会直接打这个端点。

**常见误区**：`f1.telemetry.processed`（Kafka topic）和 Prometheus 指标**是同一个
Faust 处理过程产生的两条完全独立的输出，不是先后流水线关系**：

```
faust-processor 处理每条记录
    │
    ├─→ 路径 A：把完整加工后的记录发到 f1.telemetry.processed（Kafka topic，明细事件流）
    │
    └─→ 路径 B：把统计信息（处理了多少条、多少条无效）累加进内存计数器
                通过 /metrics 暴露成文本
                        ↓
                Prometheus 周期性主动拉取，存进自己的时间序列数据库（跟 Kafka 完全独立）
                        ↓
                Grafana 查 Prometheus 画图；Alertmanager 查 Prometheus 判断要不要告警
```

一个保留**明细**（能看到具体某条记录），一个保留**统计摘要**（能看到趋势/异常），
服务目的完全不同，谁也不依赖谁。

---

## Terraform

**是什么**：Infrastructure as Code（基础设施即代码）工具。写一份声明式配置
（`.tf`，HCL 语言）描述"我要的云资源长什么样"（VPC、EKS 集群、IAM 权限等），
Terraform 自己算出"现在的真实状态"和"声明的目标状态"之间的差异，调用云厂商 API
去补上差异。

- `terraform plan`——算出要新建/改/删哪些资源，先给你看
- `terraform apply`——真正执行变更
- `terraform destroy`——反向操作，全部删掉
- **state 文件**——Terraform 自己维护的"我创建过什么"的记录，下次算差异靠它

这个"声明期望状态，工具自己算怎么达成"的哲学**跟 Kubernetes 是同一套设计思想**，
只是作用的层面不同：K8s 管"集群内部的 Pod/Service"，Terraform 管"集群本身以及
它所在的整个云环境"。

### Terraform 跟 kind 是在解决同一个问题，一个免费一个花钱

kind 是"在电脑里用 Docker 造一个假的但真实可用的 K8s 集群"；**Terraform + 真实
AWS EKS 做的是同一件事——造一个 K8s 集群——只不过是真的，要花钱**：

```
本地开发路径：   kind create cluster        → 跑在笔记本 Docker 里的 K8s 集群（免费）
真实部署路径：   Terraform（VPC/IAM/EKS）    → 跑在 AWS 上的真实 K8s 集群（计费）
```

这也是 [CLAUDE.md](../CLAUDE.md) 里"Terraform 代码要同时支持 kind provider 和真实
AWS，用变量切换"这句话的意思：同一份 Terraform 代码，改个变量，就能选择本地造假
集群还是云上造真集群，对上层（Helm/Kafka/faust-processor）完全无感知区别。

**Terraform 管的范围比 kind 大得多**：VPC/子网、IAM 权限、EKS 集群本身——这些本地
kind 完全不需要考虑（Docker 网络自动搞定），是 Terraform 专门用来处理"真实云"那部分
复杂度的。

**Terraform 跟 Helm 的关系**：Helm 只认 K8s API；Terraform 认的是各种云厂商 API
（也包括 K8s API 本身，通过 `kubernetes`/`helm` provider）。这意味着我们目前手动跑的
`kind create cluster` + `helm install kafka ...`（封装在
`scripts/setup-local-cluster.sh` 里），以后可以被一份 Terraform 配置统一接管，用
一条 `terraform apply` 把"造集群"和"装 Kafka"串起来，不用再手写 shell 脚本按顺序
调用命令——这是 Day 5-7 要做的事。

**GCP 对照**：类比"你手动用 `gcloud` 命令逐步创建资源"（命令式）vs Terraform（声明式）
——跟 K8s 里"kubectl apply 声明式模型"是同一套思路，只是作用对象从"集群内部资源"
扩大到"整个云账号"。Terraform 跨云（AWS/GCP/Azure 通用），信号价值比 GCP 专属的
Deployment Manager 更高。

---

## Dataform（跟 Terraform 名字像，但完全不相关）

**是什么**：Google 收购的工具，管理 **BigQuery 里的 SQL 数据转换流水线**——写一堆
`SELECT` 语句定义"这张表怎么从别的表算出来"，Dataform 管理表之间的依赖关系、增量
更新、数据质量断言。定位跟开源工具 **dbt**（data build tool）几乎一样，只是 Dataform
被 Google 收购后专门绑定 BigQuery，dbt 跨数仓通用。

**跟 Terraform 的区别**：两者除了名字都带"-form"、都是声明式工具之外没有任何关系：

| | Terraform | Dataform |
| --- | --- | --- |
| 管什么 | 基础设施（VPC/K8s 集群/IAM——运行环境本身） | 数据转换逻辑（数仓里表和表的 SQL 计算关系） |
| 作用的 API | 云厂商资源 API | BigQuery 查询引擎 |
| 类比 | 盖房子、拉水电 | 房子盖好后，安排东西怎么摆放整理 |

**跟本项目的关系**：完全没有，本项目架构里没有数据仓库这一层（链路止步于
`Kafka → Faust → Prometheus/Grafana`），用不上 Dataform。faust-processor 做的
"校验+特征工程"概念上是同一个"数据转换"目标，但走的是**实时流式**范式，不是
Dataform/dbt 那种**批量 SQL**范式——这跟前面"Kafka（流）vs Airflow（批）"是同一个
主题的另一个例子。

---

## Spark

**是什么**：一个分布式数据处理引擎，最初是为了取代 Hadoop MapReduce 而生，核心
能力是把巨大数据集切成很多份、分发到一堆机器上并行计算。需要一个集群才能跑
（driver 调度 + executor 实际计算）。核心抽象是 **DataFrame**——概念上是一张分布
在多台机器上的巨型表，用类似 SQL/pandas 的 API 操作。**Spark Structured Streaming**
是后来加上去的流处理能力，把 Kafka 这种流当成"无限增长的表"处理，但用的是
**微批（micro-batch）**模型（每隔几百毫秒到几秒攒一批处理），不是真正逐条处理。

**跟 Faust/Flink 是同一道题的三个候选答案**——都是"读 Kafka、做处理"这个角色的
实现方案，平级选择，不是互补关系：

| | Kafka | Faust（本项目选的） | Flink（明确弃用） | Spark Structured Streaming |
| --- | --- | --- | --- | --- |
| 角色 | 传输/存储层 | 处理引擎候选 A | 处理引擎候选 B | 处理引擎候选 C |
| 运行方式 | — | 纯 Python 单进程 | JVM 独立集群 | JVM 独立集群 |
| 处理模型 | — | 真流式（逐条） | 真流式（逐条） | 微批 |
| 最初设计目的 | 消息传输 | 流处理 | 流处理 | **批处理**（流式是后加的） |
| 运维复杂度 | — | 低，像个普通服务 | 高，独立集群+checkpoint | 高，独立集群 |

这解释了为什么 Flink 和 Spark 都没被选中：两者都属于"JVM、需要独立集群、运维成本
高"这一类，跟决策 1"把时间留给平台工程层"直接冲突。

**Spark 的老家其实是批处理，经常被 Airflow 调度**：Spark 最经典的场景是大规模批处理
ETL/机器学习训练，真实架构里常见"Airflow 的一个 DAG 任务里跑一个 Spark job"——
Airflow 负责调度，Spark 负责真正吃掉海量数据算结果。这跟本项目 Kafka+Faust 的关系
不同：这里没有调度器，Faust 是**永远在跑**的常驻服务，不是被定时触发的批任务。

**GCP 对照**：**Dataproc** 是 GCP 的托管 Spark/Hadoop 服务。

**一句话总结**：Kafka 是水管，Spark/Flink/Faust 都是接在水管上的"处理厂"候选方案，
选哪个是纯粹的工程权衡（吞吐量、延迟要求、运维成本），不是谁更高级。

---

## 常见误区（这段讨论里纠正过的）

1. ❌ "kind 集群负责处理数据" → ✅ kind 只造集群地基，处理数据是 Kafka/Faust 的事
2. ❌ "Kafka 记录了数据的'load time'" → ✅ Kafka 记的是 `CreateTime`（producer 发送
   时间）和 offset，它不理解数据内容，也不做任何处理
3. ❌ "Helm 会根据情况持续自动调整 K8s 资源" → ✅ Helm 只在你主动执行
   `install`/`upgrade` 的那一刻起作用；持续监控/自愈是 K8s controller 的工作，
   不是 Helm
4. ❌ "有新数据 = 需要新建一个 Helm" → ✅ 新数据只是更多消息发进已有 topic，跟 Helm
   毫无关系；只有装**新组件**（Grafana/Prometheus/ArgoCD）才需要新的 `helm install`
5. ❌ "存数据要经过 Helm" → ✅ 数据直接进已经在运行的 Kafka Pod，完全不经过 Helm
6. ❌ "Helm 是给 Kafka 用的仓库" → ✅ Helm 是通用施工队（工具本身装一次，反复使用），
   Kafka 部署本身才是"仓库"
7. ❌ "kind 是专门为 f1.telemetry 这个 topic 分配资源" → ✅ kind/Helm 分配的是通用
   基础设施，跟具体某个 topic 无关；topic 是 Kafka 运行起来后动态创建的，粒度比
   kind/Helm 细得多
8. ❌ "`f1.telemetry.processed` 是 dataset 或 table" → ✅ 它是 Kafka topic，跟输入
   topic 是同一类东西（事件流）；真正的"table"是 Faust 内部的
   `last_speed_kph`/`max_session_time_s` 状态存储，外部系统看不到
9. ❌ "processed topic 是把数据存进去然后能查 metrics" → ✅ Prometheus 指标和
   processed topic 是同一个 Faust 处理过程产生的两条独立输出，不是先后流水线关系
10. ❌ "Dataform 跟 Terraform 有关系" → ✅ 只是名字都带"-form"，Dataform 管数仓 SQL
    转换，Terraform 管云基础设施，完全不同领域，本项目也用不上 Dataform

---

## 已验证过的实操对照

跑过的命令 ↔ 对应概念：

| 命令 | 做了什么 |
| --- | --- |
| `kind create cluster --config infra/kind/kind-config.yaml` | 造 3 节点本地 K8s 集群 |
| `helm install kafka bitnami/kafka -f infra/helm/kafka-values.yaml` | 把 Kafka 的 K8s 资源清单提交给集群 |
| `kubectl -n pipeline get pods` | 看 K8s 实际起了哪些 Pod（`kafka-controller-0`） |
| `telemetry-generator` 连 `kafka.pipeline.svc.cluster.local:9092` | Producer 往 Kafka 发消息 |
| `kafka-get-offsets.sh --topic f1.telemetry` | 验证 offset=72130，跟 generator 发送的
  记录数精确对上 |
| `faust -A src.app worker`（`apps/faust-processor`） | Faust agent 持续消费
  `f1.telemetry`，写 `f1.telemetry.processed` |
| 对比两个 topic 的 offset（消费中途多次核对） | 每次都精确相等（如 68670==68670），
  验证零丢失零重复 |
| `curl http://localhost:6066/metrics`（经 `kubectl port-forward`） | 看到
  `f1_telemetry_records_total{driver_code="LEC"}` 等指标随处理实时更新 |

详见 [progress-log.md](progress-log.md) 里 Week 1 Day 1-2 和 Week 2 start 的完整记录。
