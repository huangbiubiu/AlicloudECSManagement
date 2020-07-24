#!/usr/bin/env python
# coding=utf-8
import json
import os
from typing import Tuple

from multiprocessing import Queue
import queue
q = queue.Queue()

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkecs.request.v20140526.StartInstanceRequest import StartInstanceRequest
from aliyunsdkecs.request.v20140526.StopInstanceRequest import StopInstanceRequest


def read_key(path: str = "./accesskey.json") -> Tuple[str, str, str]:
    if not os.path.exists(path):
        print(f"在 {path} 找不到accesskey文件!")
        raise ValueError("accesskey文件不存在")

    with open(path) as f:
        data = json.load(f)

    for field in ["accessKeyId", "accessSecret", "instanceId"]:
        if field not in data:
            print(f"不合法的json格式。 必须包含{field}字段!")
            raise ValueError("不合法的json格式")

    return data["accessKeyId"], data["accessSecret"], data['instanceId']


def describe_instance(client: AcsClient, instance_id: str):
    request = DescribeInstancesRequest()
    request.set_accept_format('json')

    request.set_InstanceIds(f'''["{instance_id}"]''')

    response = client.do_action_with_exception(request)
    response_str = response.decode()
    response_data: dict = json.loads(response_str)

    if response_data["TotalCount"] == 0:
        print(response_str)
        raise ValueError("没有可用的实例，请检查InstanceId是否正确.")

    status = response_data['Instances']['Instance'][0]['Status']

    ip = ""
    if status == "Running":
        ip_data = response_data['Instances']['Instance'][0]['PublicIpAddress']
        if "IpAddress" in ip_data and len(ip_data["IpAddress"]) > 0:
            ip = ip_data["IpAddress"][0]
    elif status == "Stopping" or status == "Starting":
        pass
    elif status == "Stopped":
        pass
    else:
        print(response_str)
        raise ValueError(f"无效的状态: {status}")

    return status, ip


def start_instance(client: AcsClient, instance_id: str):
    request = StartInstanceRequest()
    request.set_accept_format('json')

    request.set_InstanceId(instance_id)

    try:
        response = client.do_action_with_exception(request)
    except (ServerException, ClientException) as e:
        print("启动失败.")
        print(e.error_code)
        raise e

    print("启动成功! 请等待一分钟左右，服务器即可用。")
    print("稍等片刻后可以使用status命令获取服务器IP地址。")


def stop_instance(client, instance_id):
    request = StopInstanceRequest()
    request.set_accept_format('json')

    request.set_InstanceId(instance_id)
    request.set_StoppedMode("StopCharging")

    try:
        response = client.do_action_with_exception(request)
    except (ServerException, ClientException) as e:
        print(e.error_code)
        print("关机失败")
        raise e

    print("关机成功!")

    pass


def init_client() -> Tuple[AcsClient, str]:
    access_key, access_secret, instance_id = read_key()
    client = AcsClient(access_key, access_secret, 'cn-shenzhen')

    return client, instance_id


def test():
    client, instance_id = init_client()
    # status, ip = describe_instance(client, instance_id)
    start_instance(client, instance_id)

    pass


def pretty_print_status(status, ip) -> str:
    str_builder = ["*****服务器状态*****", f"服务器状态: {status}", f"服务器公网IP地址: {ip}", "\n"]

    return "\n".join(str_builder)


def help_command() -> str:
    help_text = """
    Minecraft 服务器控制台
    帮助文档
    
    > help: 打印帮助指令
    > status: 获取服务器状态
    > start: 开启服务器。注意：本命令只能在服务器状态为Running时使用。
    > stop: 停止服务器。注意：本命令只能在服务器状态为Stopped时使用。
    > exit: 退出服务器控制台
    """

    return help_text


def cil():
    print("Minecraft 服务器控制台")
    print("首次启动，检查服务器状态中...")

    try:
        client, instance_id = init_client()
        status, ip = describe_instance(client, instance_id)
        print(pretty_print_status(status, ip))
    except Exception as e:
        print(e)
        print("遇到错误。按任意键退出。")
        input()
        return 

    print("输入help获取帮助...")
    while True:
        command = input("> ")
        command = str.lower(command)  # case insensitive

        try:
            if command == 'help':
                print(help_command())
            elif command == 'status':
                status, ip = describe_instance(client, instance_id)
                print(pretty_print_status(status, ip))
            elif command == "start":
                print("启动服务器...")
                print("获取服务器状态...")
                status, ip = describe_instance(client, instance_id)
                if status != "Stopped":
                    print(f"服务器状态为{status}, 不能启动。")
                else:
                    start_instance(client, instance_id)
            elif command == 'stop':
                print('关闭服务器...')
                print("获取服务器状态...")
                status, ip = describe_instance(client, instance_id)
                if status != "Running":
                    print(f"服务器状态为{status}, 不能关闭。")
                else:
                    stop_instance(client, instance_id)
            elif command == 'exit':
                print("正在关闭控制台...")
                break
            else:
                print(f"无效的命令：{command}, 请检查后重新输入。")
                print(help_command())

        except Exception as e:
            print("出现异常：")
            print(e)

            print(f"本次命令({command})执行失败")

        print()


if __name__ == '__main__':
    cil()
