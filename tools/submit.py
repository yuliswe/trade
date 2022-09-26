#!python3
from contextlib import contextmanager
import math
from pathlib import Path
from subprocess import run
import sys
import time
from typing import ContextManager, Generator
import boto3
import paramiko


class EC2LaunchTemplate:
    computing_32 = "lt-00b8fcf9a488071fc"
    min_experiment = "lt-087d8a839941d13fb"
    max_computing = "max_computing"


ec2r = boto3.resource("ec2")
ec2 = ec2r.meta.client

ecs = boto3.client("ecs")


image_name = "ghcr.io/ylilarry/trade"
github_token = "aws_account_id"
launch_template = EC2LaunchTemplate.min_experiment
ssh_key_files = [
    Path.home().absolute() / ".ssh/ec2-launch-template.ed25519.pub",
    Path.home().absolute() / ".ssh/ec2-launch-template.ed25519",
]

if session := boto3._get_default_session():
    aws_region = session.region_name

if aws_account_info := boto3.client("sts").get_caller_identity():
    aws_account_id = aws_account_info["Account"]
    aws_account_arn = aws_account_info["Arn"]
    aws_account_userid = aws_account_info["UserId"]


def create_instance() -> ec2r.Instance:
    print("Creating instance")
    [instance, *_] = ec2r.create_instances(
        MinCount=1,
        MaxCount=1,
        LaunchTemplate={
            "LaunchTemplateId": launch_template,
            "Version": "$Latest",
        },
    )
    instance.wait_until_running()
    instance.reload()
    return instance


@contextmanager
def InstancePool() -> ec2r.Instance:
    instance = create_instance()
    try:
        yield instance
    finally:
        all_terminate()


def list_running_instances() -> list[str]:
    response = ec2.describe_instances(
        Filters=[
            {
                "Name": "instance-state-name",
                "Values": ["running"],
            },
        ]
    )
    instances = []
    for resv in response["Reservations"]:
        for instance in resv["Instances"]:
            instances.append(instance["InstanceId"])
    return instances


def list_unterminated_instances() -> list[str]:
    response = ec2.describe_instances(
        Filters=[
            {
                "Name": "instance-state-name",
                "Values": [
                    "pending",
                    "running",
                    "shutting-down",
                    "stopping",
                    "stopped",
                ],
            },
        ]
    )
    instances = []
    for resv in response["Reservations"]:
        for instance in resv["Instances"]:
            instances.append(instance["InstanceId"])
    return instances


def all_stop():
    if not (instances := list_running_instances()):
        return
    print(f"Stopping {instances}")
    ec2.stop_instances(InstanceIds=instances)
    for ins_id in instances:
        ins = ec2r.Instance(ins_id)
        ins.wait_until_stopped()


def all_terminate():
    if not (instances := list_unterminated_instances()):
        return
    print(f"Terminating {instances}")
    ec2.terminate_instances(InstanceIds=instances)
    for ins_id in instances:
        ins = ec2r.Instance(ins_id)
        ins.wait_until_terminated()


def run_trade(instance: ec2r.Instance):
    response = ecs.register_task_definition(
        family="trade",
        containerDefinitions=[
            {
                "name": image_name,
                "image": image_name,
                "repositoryCredentials": {
                    "credentialsParameter": f"arn:aws:secretsmanager:{aws_region}:{aws_account_id}:secret:secret_name"
                },
            }
        ],
    )
    task_arn = response["taskDefinition"]["taskDefinitionArn"]
    try:
        ecs.run_task(cluster="trade", taskDefinition=task_arn, count=1)
        waiter = ecs.get_waiter("tasks_stopped")
        waiter.wait(
            cluster="trade",
            tasks=[task_arn],
            WaiterConfig={"Delay": 10, "MaxAttempts": math.inf},
        )
    finally:
        ecs.deregister_task_definition(task_arn)


def shell(*args, **kwargs):
    return run(args, shell=True, check=True, **kwargs)


def push_build():
    shell("docker-compose build")
    shell("docker-compose push")


class SSHConnectionExec:
    def __init__(self, para: paramiko.SSHClient) -> None:
        self.para = para

    def __call__(self, cmd: str):
        print("> " + cmd, flush=True)
        stdin, stdout, stderr = self.para.exec_command(cmd)
        for ln in stderr:
            print(ln, end="", flush=True)
        for ln in stdout:
            print(ln, end="", flush=True)


@contextmanager
def SSHConnection(instance: ec2r.Instance) -> ContextManager[SSHConnectionExec]:
    with paramiko.SSHClient() as ssh:
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.WarningPolicy)
        attempts = 0
        print("Connecting", flush=True)
        while True:
            attempts += 1
            try:
                ssh.connect(
                    hostname=instance.public_ip_address,
                    username="ubuntu",
                    timeout=5,
                    banner_timeout=5,
                    # key_filename=[str(x) for x in ssh_key_files],
                )
            except Exception:
                if attempts == 1:
                    print("Connection failed, retrying", flush=True)
                if attempts <= 12:
                    time.sleep(10)
                    continue
                else:
                    raise
            else:
                yield SSHConnectionExec(ssh)
                break


def main():
    push_build()
    with InstancePool() as instance:
        print(instance.id, instance.public_ip_address)
        with SSHConnection(instance) as ssh:
            ssh("docker pull " + image_name)
            ssh("docker run -t trader {image_name} --plot")
            ssh("docker cp trader:plot.html ~/plot.html")
            ssh("docker container prune -f")


main()
