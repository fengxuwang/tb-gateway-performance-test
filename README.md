# Protocol Simulators for ThingsBoard Gateway

高性能协议模拟器，用于 ThingsBoard Gateway 性能测试。

## 功能特性

- ✅ 多协议架构支持（BACnet，更多协议开发中）
- ✅ 模拟多个协议设备，每个设备支持大量对象
- ✅ 支持生成多个连接器配置，每个连接器独立配置
- ✅ 自动生成完整的 ThingsBoard Gateway 配置文件
- ✅ 支持自定义轮询周期和上报策略
- ✅ 灵活的数据更新控制

## 安装

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 快速开始

### 1. 查看帮助

```bash
# 查看主帮助
python main.py --help

# 查看特定协议帮助
python main.py bacnet --help
```

### 2. 启动模拟器

```bash
# BACnet 示例
python main.py bacnet --devices 1 --analog-inputs 30

# 仅生成配置文件
python main.py bacnet --devices 1 --analog-inputs 30 --generate-config-only
```

### 3. 查看可用协议

```bash
python main.py --help
```

---

## 协议支持

### BACnet

BACnet 楼宇自动化协议模拟器，支持完整的对象类型和数据模拟。

#### 快速开始

```bash
# 小规模测试
python main.py bacnet --devices 1 --analog-inputs 10

# 性能测试
python main.py bacnet --devices 1 --analog-inputs 30 --poll-period 5000

# 使用 reportStrategy 配置
python main.py bacnet \
  --devices 1 --analog-inputs 30 \
  --report-strategy ON_REPORT_PERIOD --report-period 5000 \
  --timeseries-report-strategy ON_CHANGE_OR_REPORT_PERIOD --timeseries-report-period 3000

# 禁用数据更新（保持初始值）
python main.py bacnet --devices 1 --analog-inputs 30 --no-data-update
```

#### BACnet 特定参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--base-port` | int | 47809 | 设备 UDP 端口起始值 |
| `--base-device-id` | int | 100 | BACnet 设备 ID 起始值 |
| `--analog-inputs` | int | - | AnalogInput 对象数量 |
| `--analog-outputs` | int | - | AnalogOutput 对象数量 |
| `--analog-values` | int | - | AnalogValue 对象数量 |
| `--binary-inputs` | int | - | BinaryInput 对象数量 |
| `--binary-outputs` | int | - | BinaryOutput 对象数量 |
| `--binary-values` | int | - | BinaryValue 对象数量 |
| `--multistate-inputs` | int | - | MultiStateInput 对象数量 |
| `--multistate-outputs` | int | - | MultiStateOutput 对象数量 |
| `--multistate-values` | int | - | MultiStateValue 对象数量 |

如果未指定对象类型参数，系统会自动按比例分配对象。

#### BACnet 测试工具

使用内置的 BACnet 客户端测试工具验证模拟器：

```bash
# 读取单个点位
python bacnet_client.py read --object-type analogInput --object-id 1

# 测试连续点位（1-30）
python bacnet_client.py test-range --start 1 --count 30

# 测试批量读取（模拟 Gateway 行为）
python bacnet_client.py test-batch --batch-size 30 --count 30

# 获取设备对象列表
python bacnet_client.py object-list

# 发现 BACnet 设备
python bacnet_client.py discover
```

#### BACnet 使用示例

```bash
# 示例 1：快速测试（小规模）
python main.py bacnet --devices 1 --analog-inputs 5 --poll-period 1000

# 示例 2：性能测试（中规模）
python main.py bacnet --devices 1 \
  --analog-inputs 30 \
  --binary-inputs 10 \
  --analog-values 20 \
  --poll-period 5000

# 示例 3：压力测试（大规模）
python main.py bacnet --devices 10 \
  --objects-per-device 100 \
  --poll-period 10000

# 示例 4：多连接器配置（3 个连接器，每个 2 个设备）
python main.py bacnet --devices 2 --connectors 3 --analog-inputs 10 --generate-config-only

# 示例 5：跨机器访问
python main.py bacnet --devices 1 --analog-inputs 30 --gateway-host 192.168.1.100

# 示例 6：Docker 环境
python main.py bacnet --devices 1 --analog-inputs 30 --ip 0.0.0.0 --gateway-host host.docker.internal
```

#### BACnet 技术细节

**支持的对象类型**：

| 对象类型 | 类型值 | 说明 |
|---------|-------|------|
| AnalogInput | 0 | 模拟输入（温度、湿度等） |
| AnalogOutput | 1 | 模拟输出 |
| AnalogValue | 2 | 模拟值 |
| BinaryInput | 3 | 二进制输入（开关状态） |
| BinaryOutput | 4 | 二进制输出 |
| BinaryValue | 5 | 二进制值 |
| MultiStateInput | 13 | 多状态输入 |
| MultiStateOutput | 14 | 多状态输出 |
| MultiStateValue | 19 | 多状态值 |

**模拟器特性**：
- 基于 `bacpypes3` 库实现
- 支持 BACnet/IP 协议
- 分段传输支持（segmentedBoth）
- 大 APDU 缓冲区（65535 字节）
- 动态数据更新（随机游走算法）

---

### Modbus

> 即将推出...

---

## 通用参数说明

### 模拟器参数（所有协议通用）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--devices` | int | 1 | **每个连接器**的设备数量 |
| `--connectors` | int | 1 | 生成的连接器配置文件数量（1-N） |
| `--objects-per-device` | int | 10 | 每个设备的对象总数 |
| `--update-interval` | float | 5.0 | 数据更新间隔（秒） |
| `--ip` | str | auto | 模拟器绑定 IP 地址（自动检测本地 IPv4） |
| `--gateway-host` | str | auto | Gateway 连接地址（默认使用 `--ip` 值） |
| `--poll-period` | int | 5000 | Gateway 轮询周期（毫秒） |
| `--report-strategy` | str | ON_RECEIVED | 设备级上报策略 |
| `--report-period` | int | 10000 | 设备级上报周期（毫秒） |
| `--timeseries-report-strategy` | str | - | 时序数据条目级上报策略（默认使用 `--report-strategy` 值） |
| `--timeseries-report-period` | int | - | 时序数据上报周期（毫秒，默认使用 `--report-period` 值） |
| `--no-data-update` | flag | false | 禁用数据自动更新，保持初始值不变 |

### 配置生成参数

| 参数 | 说明 |
|------|------|
| `--config-dir` | 配置文件输出目录（默认：config/） |
| `--generate-config-only` | 仅生成配置文件，不启动模拟器 |
| `--log-level` | 日志级别（DEBUG/INFO/WARNING/ERROR） |

### IP 地址配置说明

**IP 地址自动检测**：
- `--ip` 默认会自动检测当前机器的本地 IPv4 地址
- 生成的配置文件会使用检测到的 IP，无需手动配置
- 如需手动指定，可以覆盖 `--ip` 参数（如 `--ip 0.0.0.0` 或 `--ip 192.168.1.50`）

**`--gateway-host` 参数说明**：

| `--ip` 设置 | `--gateway-host` 设置 | 最终 Gateway 连接地址 |
|-------------|---------------------|---------------------|
| 未指定（自动检测） | 未指定 | 自动检测的 IP |
| 未指定 | 指定值 | 指定值（优先使用） |
| `0.0.0.0` | 未指定 | `0.0.0.0` |
| 具体IP | 指定值 | 指定值（优先使用） |

**使用场景**：
- **本地测试**：直接使用默认值，IP 自动检测
- **跨机器访问**：模拟器使用自动检测的 IP，无需额外配置
- **Docker 环境**：设置 `--gateway-host host.docker.internal`

### 生成的配置文件

使用多连接器模式时，会生成以下文件（默认保存在 `config/` 目录）：

| 文件 | 说明 |
|------|------|
| `config/tb_gateway.json` | ThingsBoard Gateway 主配置文件（包含 thingsboard、storage、connectors） |
| `config/{protocol}_1.json` | 连接器 1 的配置（如 bacnet_1.json） |
| `config/{protocol}_2.json` | 连接器 2 的配置 |
| `...` | 更多连接器配置文件 |
| `config/{protocol}_N.json` | 第 N 个连接器的配置 |

**单连接器模式**（`--connectors 1`）：
- 生成 `config/tb_gateway.json` 和 `config/{protocol}_1.json`

**自定义配置目录**：
```bash
# 使用自定义目录
python main.py bacnet --devices 5 --config-dir my_configs --generate-config-only

# 生成的文件保存在 my_configs/ 目录
```

---

## ReportStrategy 参数说明

`reportStrategy` 控制数据上报到 ThingsBoard 的策略，所有协议通用。

### 可用策略

| 策略 | 说明 | 需要 reportPeriod |
|------|------|-------------------|
| `ON_RECEIVED` | 收到数据时立即上报（默认） | 否 |
| `ON_CHANGE` | 数据变化时上报 | 否 |
| `ON_REPORT_PERIOD` | 按周期上报 | 是 |
| `ON_CHANGE_OR_REPORT_PERIOD` | 变化或周期上报 | 是 |
| `DISABLED` | 禁用上报 | 否 |

### 使用示例

```bash
# 设备级按周期上报（5秒）
python main.py bacnet --report-strategy ON_REPORT_PERIOD --report-period 5000

# 时序数据按变化或周期上报（3秒）
python main.py bacnet --timeseries-report-strategy ON_CHANGE_OR_REPORT_PERIOD --timeseries-report-period 3000

# 两者同时配置
python main.py bacnet \
  --devices 1 --analog-inputs 30 \
  --report-strategy ON_REPORT_PERIOD --report-period 5000 \
  --timeseries-report-strategy ON_CHANGE_OR_REPORT_PERIOD --timeseries-report-period 3000

# 禁用数据更新，保持初始值不变（用于测试）
python main.py bacnet --devices 1 --analog-inputs 30 --no-data-update
```

**注意**：
- 设备级 `reportStrategy` 应用于整个设备
- 时序数据条目级 `reportStrategy` 应用于每个对象
- `reportPeriod` 只在策略为 `ON_REPORT_PERIOD` 或 `ON_CHANGE_OR_REPORT_PERIOD` 时才需要
- `--no-data-update` 禁用数据自动更新，适合需要稳定初始值的测试场景

---

## 快速参考

### 常用场景速查

| 场景 | 命令 |
|------|------|
| 小规模测试 | `python main.py bacnet --devices 1 --analog-inputs 10 --poll-period 5000` |
| 中规模测试 | `python main.py bacnet --devices 1 --analog-inputs 30 --poll-period 5000` |
| 仅生成配置 | 添加 `--generate-config-only` |
| 跨机器访问 | 使用自动检测的 IP，无需额外配置 |
| Docker 环境 | 添加 `--gateway-host host.docker.internal` |

### pollPeriod 快速参考

| 场景 | 命令 |
|------|------|
| 实时监控 | `--poll-period 1000` |
| 标准监控 | `--poll-period 5000` |
| 默认配置 | `--poll-period 10000` |
| 低频轮询 | `--poll-period 60000` |

### 多连接器配置快速参考

| 场景 | 命令 |
|------|------|
| 单连接器（默认） | `--connectors 1` |
| 3 个连接器 | `--connectors 3 --devices 2` |
| 大规模测试 | `--connectors 10 --devices 10` |

**参数说明**：
- `--devices N`：**每个连接器**的设备数量
- `--connectors M`：生成 M 个连接器配置文件
- 总设备数 = N × M

### 常见问题速查

| 问题 | 解决方案 |
|------|---------|
| 只能读到 1-4 个点位（BACnet） | 确保使用最新代码（APDU=65535） |
| 找不到设备 | 检查模拟器是否运行：`ps aux \| grep main.py` |
| 配置无效 | 使用生成的 `tb_gateway.json` 和协议配置文件 |
| tb_gateway.json 报错 | 确保包含 thingsboard、storage、connectors 三个部分 |

---

## ThingsBoard Gateway 配置

### 1. 将生成的配置复制到 Gateway

```bash
# 复制整个配置目录到 Gateway 配置目录
cp -r config/ /path/to/gateway/config/

# 或者复制单个文件
cp config/tb_gateway.json /path/to/gateway/config/
cp config/*.json /path/to/gateway/config/
```

### 2. 配置文件说明

生成的 `tb_gateway.json` 包含完整的 Gateway 配置：

```json
{
  "thingsboard": {
    "host": "localhost",
    "port": 1883,
    "remoteShell": false,
    "remoteConfiguration": false,
    "security": {
      "type": "basic",
      "username": "YOUR_USERNAME",
      "password": "YOUR_PASSWORD"
    }
  },
  "storage": {
    "type": "memory",
    "read_records_count": 100,
    "max_records_count": 100000,
    "data_folder_path": "./data/"
  },
  "connectors": [
    {
      "name": "BACnet-Connector-1",
      "type": "bacnet",
      "configuration": "bacnet_1.json"
    },
    {
      "name": "BACnet-Connector-2",
      "type": "bacnet",
      "configuration": "bacnet_2.json"
    }
  ]
}
```

### 3. 修改 ThingsBoard 连接信息

编辑 `tb_gateway.json`，修改 ThingsBoard 服务器连接信息：

```json
{
  "thingsboard": {
    "host": "your-thingsboard-server.com",  // 修改为实际的 ThingsBoard 服务器地址
    "port": 1883,                            // MQTT 端口
    "security": {
      "username": "your-username",           // 修改为实际的用户名
      "password": "your-password"            // 修改为实际的密码
    }
  }
}
```

### 4. 重启 Gateway

```bash
sudo systemctl restart thingsboard-gateway
# 或
./thingsboard-gateway.sh restart
```

### 5. 验证配置

查看 Gateway 日志确认所有连接器启动成功：

```bash
tail -f /var/log/thingsboard-gateway/thingsboard-gateway.log | grep -i bacnet
```

预期输出：
```
[INFO] - Starting BACnet Connector: BACnet-Connector-1
[INFO] - Starting BACnet Connector: BACnet-Connector-2
[INFO] - BACnet Connector-1: Connected to device BACnet-Sim-0001
[INFO] - BACnet Connector-2: Connected to device BACnet-Sim-0003
```

---

## 常见问题

### BACnet 特定问题

#### 1. 只能读取到 analogInput 1-4

**原因**：APDU 大小限制（默认 1476 字节）

**解决**：本模拟器已将 APDU 大小增加到 65535 字节，确保：
- 模拟器使用最新代码（已修改 `maxApduLengthAccepted`）
- Gateway 配置也使用相同的 APDU 大小
- 使用生成的配置文件

#### 2. 找不到 BACnet 设备

**检查**：
```bash
# 确认模拟器正在运行
ps aux | grep main.py

# 使用客户端发现设备
python bacnet_client.py discover
```

#### 3. 对象列表不完整

**验证**：
```bash
# 获取设备对象列表
python bacnet_client.py object-list

# 检查对象数量是否正确
```

---

## 项目结构

```
.
├── main.py                      # CLI 入口点（分发器）
├── cli/                         # CLI 包
│   ├── __init__.py
│   ├── base.py                  # 共享 CLI 逻辑
│   ├── bacnet.py                # BACnet 子命令
│   └── modbus.py                # Modbus 子命令（未来）
├── simulators/                  # 模拟器包
│   ├── __init__.py
│   ├── base.py                  # 抽象基类
│   ├── utils.py                 # 通用工具
│   ├── bacnet/                  # BACnet 模拟器
│   │   ├── __init__.py
│   │   └── simulator.py
│   └── modbus/                  # Modbus 模拟器（未来）
│       ├── __init__.py
│       └── simulator.py
├── config/                      # 生成的配置文件目录（默认）
│   ├── tb_gateway.json          # Gateway 主配置文件
│   ├── bacnet_1.json            # BACnet 连接器 1 配置
│   └── bacnet_N.json            # BACnet 连接器 N 配置
├── bacnet_client.py             # BACnet 客户端测试工具
├── requirements.txt             # Python 依赖
└── README.md                    # 本文档
```

---

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
