#!/usr/bin/env python3
"""
BACnet Client - 用于测试 BACnet 模拟器的点位读取

功能：
- 读取指定对象的 presentValue
- 批量读取多个对象
- 发现设备和对象列表
- 诊断 APDU 大小问题
"""
import argparse
import asyncio
import sys
from bacpypes3.pdu import Address
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.local.device import DeviceObject


class BACnetTestClient:
    def __init__(self, host="127.0.0.1", port=47809):
        self.host = host
        self.port = port
        self.app = None

    async def connect(self):
        """连接到 BACnet 网络"""
        device_obj = DeviceObject(
            objectIdentifier=("device", 999),  # 测试客户端设备 ID
            objectName="BACnet-Test-Client",
            vendorIdentifier=999,
            vendorName="TestClient",
            protocolVersion=1,
            protocolRevision=22,
        )
        # 使用随机端口避免冲突
        import random
        bind_port = random.randint(47820, 47900)
        bind_address = Address(f"0.0.0.0:{bind_port}")
        self.app = NormalApplication(device_object=device_obj, local_address=bind_address)
        print(f"✓ 已连接到 BACnet 网络 (本地: {bind_address})")

    async def read_property(self, device_address, object_type, object_id, property_id="presentValue"):
        """读取单个属性"""
        try:
            # 确保使用正确的 BACnet 对象标识符格式
            from bacpypes3.primitivedata import ObjectIdentifier
            obj_id = ObjectIdentifier(f"{object_type},{object_id}")
            target_address = Address(device_address)

            result = await self.app.read_property(
                address=target_address,
                objid=obj_id,
                prop=property_id,
            )

            return result
        except Exception as e:
            return {"error": str(e)}

    async def read_multiple(self, device_address, objects):
        """批量读取多个对象 (ReadPropertyMultiple)"""
        try:
            target_address = Address(device_address)

            # 构建读取访问规范列表
            from bacpypes3.basetypes import ReadAccessSpecification, PropertyIdentifier
            from bacpypes3.constructeddata import SequenceOf
            from bacpypes3.primitivedata import ObjectIdentifier

            read_access_specs = []
            for obj in objects:
                obj_id = ObjectIdentifier(f"{obj['object_type']},{obj['object_id']}")
                prop = PropertyIdentifier(obj.get('property_id', 'presentValue'))

                ras = ReadAccessSpecification(
                    objectIdentifier=obj_id,
                    listOfPropertyReferences=[prop],
                )
                read_access_specs.append(ras)

            # 发送 ReadPropertyMultiple 请求
            from bacpypes3.apdu import ReadPropertyMultipleRequest

            request = ReadPropertyMultipleRequest(
                listOfReadAccessSpecs=SequenceOf(ReadAccessSpecification)(read_access_specs),
                destination=target_address,
            )

            result = await self.app.request(request)

            # 解析结果
            results = []
            for item in result.listOfReadAccessResults:
                obj_id = item.objectIdentifier
                # 属性名是 listOfResults
                for prop_result in item.listOfResults:
                    if hasattr(prop_result, 'readResult'):
                        value_choice = prop_result.readResult
                        # 从 ReadAccessResultElementChoice 提取 propertyValue
                        if hasattr(value_choice, 'propertyValue'):
                            actual_value = value_choice.propertyValue
                            # 如果是 Any 对象，提取实际值
                            if hasattr(actual_value, 'get_value'):
                                actual_value = actual_value.get_value()
                        else:
                            actual_value = value_choice
                        results.append({
                            'object_type': obj_id[0],
                            'object_id': obj_id[1],
                            'property_id': prop_result.propertyIdentifier,
                            'value': actual_value
                        })
            return results

        except Exception as e:
            return {"error": str(e)}

    async def discover_devices(self, target_address=None, timeout=5):
        """发现 BACnet 设备"""
        try:
            search_address = Address(target_address) if target_address else None
            devices = await self.app.who_is(address=search_address, timeout=timeout)

            results = []
            for device_info in devices:
                results.append({
                    'device_id': device_info[1],
                    'address': str(device_info.pduSource),
                })

            return results
        except Exception as e:
            return {"error": str(e)}

    async def get_object_list(self, device_address, device_id=100):
        """获取设备的对象列表"""
        try:
            from bacpypes3.primitivedata import ObjectIdentifier
            target_address = Address(device_address)
            obj_id = ObjectIdentifier(f"device,{device_id}")

            # 读取 objectList 属性
            object_list = await self.app.read_property(
                address=target_address,
                objid=obj_id,
                prop="objectList",
            )

            return object_list
        except Exception as e:
            return {"error": str(e)}

    async def test_analog_inputs_range(self, device_address, start_id=1, count=30):
        """测试读取连续的 analogInput 对象"""
        print(f"\n{'='*60}")
        print(f"测试 analogInput 对象 (ID: {start_id}-{start_id + count - 1})")
        print(f"{'='*60}")

        results = {
            'success': [],
            'failed': []
        }

        for i in range(start_id, start_id + count):
            result = await self.read_property(
                device_address=device_address,
                object_type="analogInput",
                object_id=i
            )

            if isinstance(result, dict) and 'error' in result:
                results['failed'].append({
                    'object_id': i,
                    'error': result['error']
                })
                print(f"✗ analogInput:{i} - 错误: {result['error'][:50]}")
            else:
                results['success'].append({
                    'object_id': i,
                    'value': result
                })
                print(f"✓ analogInput:{i} = {result}")

        return results

    async def test_read_multiple_batch(self, device_address, batch_size=10, total_count=30):
        """测试批量读取（模拟 Gateway 的 ReadPropertyMultiple）"""
        print(f"\n{'='*60}")
        print(f"测试 ReadPropertyMultiple (批量读取)")
        print(f"批次大小: {batch_size}, 总数: {total_count}")
        print(f"{'='*60}")

        objects = []
        for i in range(1, total_count + 1):
            objects.append({
                'object_type': 'analogInput',
                'object_id': i,
                'property_id': 'presentValue'
            })

        # 分批读取
        all_results = []
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            print(f"\n批次 {i//batch_size + 1}: 读取 {len(batch)} 个对象...")

            result = await self.read_multiple(device_address, batch)

            if isinstance(result, dict) and 'error' in result:
                print(f"✗ 批次失败: {result['error']}")
            else:
                for item in result:
                    if 'error' in item:
                        print(f"✗ {item['object_type']}:{item['object_id']} - 错误")
                    else:
                        # 处理值对象
                        val = item['value']
                        print(f"✓ {item['object_type']}:{item['object_id']} = {val}")
                        all_results.append(item)

        return all_results

    def close(self):
        """关闭连接"""
        if self.app:
            self.app.close()


async def main():
    parser = argparse.ArgumentParser(
        description='BACnet 客户端测试工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 发现设备
  python bacnet_client.py discover

  # 读取单个点位
  python bacnet_client.py read --object-type analogInput --object-id 1

  # 测试 analogInput 1-30
  python bacnet_client.py test-range --start 1 --count 30

  # 测试批量读取 (模拟 Gateway)
  python bacnet_client.py test-batch --batch-size 10 --count 30

  # 获取设备对象列表
  python bacnet_client.py object-list
        """
    )

    parser.add_argument('--host', default='127.0.0.1', help='BACnet 设备地址')
    parser.add_argument('--port', type=int, default=47809, help='BACnet 设备端口')

    subparsers = parser.add_subparsers(dest='command', help='命令')

    # discover 命令
    subparsers.add_parser('discover', help='发现 BACnet 设备')

    # read 命令
    read_parser = subparsers.add_parser('read', help='读取单个属性')
    read_parser.add_argument('--object-type', default='analogInput', help='对象类型')
    read_parser.add_argument('--object-id', type=int, default=1, help='对象 ID')
    read_parser.add_argument('--property-id', default='presentValue', help='属性 ID')

    # test-range 命令
    range_parser = subparsers.add_parser('test-range', help='测试读取连续对象')
    range_parser.add_argument('--start', type=int, default=1, help='起始 ID')
    range_parser.add_argument('--count', type=int, default=30, help='对象数量')
    range_parser.add_argument('--device-id', type=int, default=100, help='设备 ID')

    # test-batch 命令
    batch_parser = subparsers.add_parser('test-batch', help='测试批量读取')
    batch_parser.add_argument('--batch-size', type=int, default=10, help='批次大小')
    batch_parser.add_argument('--count', type=int, default=30, help='总对象数')

    # object-list 命令
    list_parser = subparsers.add_parser('object-list', help='获取设备对象列表')
    list_parser.add_argument('--device-id', type=int, default=100, help='设备 ID')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    client = BACnetTestClient(host=args.host, port=args.port)
    await client.connect()

    try:
        device_address = f"{args.host}:{args.port}"

        if args.command == 'discover':
            print("\n正在发现 BACnet 设备...")
            devices = await client.discover_devices(device_address, timeout=5)

            if isinstance(devices, dict) and 'error' in devices:
                print(f"✗ 发现失败: {devices['error']}")
            else:
                print(f"\n发现 {len(devices)} 个设备:")
                for dev in devices:
                    print(f"  - 设备 ID: {dev['device_id']}, 地址: {dev['address']}")

        elif args.command == 'read':
            print(f"\n读取 {args.object_type}:{args.object_id}.{args.property_id}...")
            result = await client.read_property(
                device_address=device_address,
                object_type=args.object_type,
                object_id=args.object_id,
                property_id=args.property_id
            )

            if isinstance(result, dict) and 'error' in result:
                print(f"✗ 读取失败: {result['error']}")
            else:
                print(f"✓ 值: {result}")

        elif args.command == 'test-range':
            results = await client.test_analog_inputs_range(
                device_address=device_address,
                start_id=args.start,
                count=args.count
            )

            print(f"\n{'='*60}")
            print(f"测试结果: 成功 {len(results['success'])} 个, 失败 {len(results['failed'])} 个")
            print(f"{'='*60}")

        elif args.command == 'test-batch':
            results = await client.test_read_multiple_batch(
                device_address=device_address,
                batch_size=args.batch_size,
                total_count=args.count
            )

            print(f"\n{'='*60}")
            print(f"批量读取完成: 共 {len(results)} 个对象")
            print(f"{'='*60}")

        elif args.command == 'object-list':
            print(f"\n获取设备 {args.device_id} 的对象列表...")
            object_list = await client.get_object_list(
                device_address=device_address,
                device_id=args.device_id
            )

            if isinstance(object_list, dict) and 'error' in object_list:
                print(f"✗ 获取失败: {object_list['error']}")
            else:
                print(f"\n对象列表 (共 {len(object_list)} 个):")
                for obj in object_list:
                    print(f"  - {obj[0]}:{obj[1]}")

    finally:
        client.close()
        print("\n连接已关闭")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)
