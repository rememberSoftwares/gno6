import re
import subprocess

from typing_extensions import List
from yacana import ToolError


def call_kubectl_cmd(cmd: str):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, timeout=20,
                                       universal_newlines=True)
    except subprocess.CalledProcessError as e:
        raise ToolError(repr(
            e.output) + '\nRemember that you must call this tool with a kubectl action and a kubectl resource. For instance: {"action_verb": "get", "resource": "pod"}')


def get_cmd_help(action_verb: str, resource_type: str) -> str:

    all_k8s_resources: str = call_kubectl_cmd("kubectl api-resources --no-headers=true")

    pattern = r"(^[a-z]+) +(?:([a-z]+)(?:,?([a-z]+))?)? .* ([A-Za-z]+)$"

    regex = re.compile(pattern, re.MULTILINE)
    # Find all matches in the string
    matches = regex.findall(all_k8s_resources)
    all_kinds: List[str] = [value.lower() for match in matches for value in match if value]

    if not (resource_type.lower() in all_kinds):
        raise ToolError(f"Invalid value for 'resource_type' parameter. Must be one of these values: {str(all_kinds)}.")

    tmp: str = call_kubectl_cmd(f"kubectl {action_verb} {resource_type} --help")
    return tmp
