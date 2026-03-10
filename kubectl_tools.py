import questionary
import time, subprocess
import config
from yacana import ToolError
from utils import *

def call_helm_cmd(cmd: str):
  print(f"```\n{cmd}\n```")
  if not isinstance(cmd, str):
    raise ToolError(f"Tool argument `cmd` MUST be of type string. Got {type(cmd)}.")

  split_cmd = cmd.split(" ")
  if len(split_cmd) < 3:
    raise ToolError(f"An automatic validation rule blocked this helm command. The command is required to be split in 3 parts: 'helm', 'action' and 'path'. A command cannot have less than 3 space divided section.")

  if split_cmd[0] != "helm":
    raise ToolError(f"Command must start with 'helm'.")

  try:
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, timeout=20, universal_newlines=True)
    if config.g_print_tool_output:
      print(f"{ANSI_CYAN}{output}{ANSI_RESET}")
    return output
  except subprocess.CalledProcessError as e:
    raise ToolError(repr(e.output))
  except subprocess.TimeoutExpired as e:
    return f"Command timed out after {e.timeout}s: {cmd}"

def call_kubectl_cmd(cmd: str):
  """
  Executes a kubectl command
  """
  print(f"```\n{cmd}\n```")
  if not isinstance(cmd, str):
    raise ToolError(f"Tool argument `cmd` MUST be of type string. Got {type(cmd)}.")

  split_cmd = cmd.split(" ")
  if len(split_cmd) < 3:
    raise ToolError(f"An automatic validation rule blocked this kubectl command. The command is required to be split in 3 parts: 'kubectl', 'verb' and 'resource'. A command cannot have less than 3 space divided section.")

  if split_cmd[0] != "kubectl":
    raise ToolError(f"Command must start with 'kubectl'.")

  # Ordering kubectl parameter for easyer parsing
  if split_cmd[1] == "-n" or split_cmd[1] == "--namespace":
    endpoint, api_key, model, endpoint_provider, log_level = get_config_from_env()
    agent = init_agent(endpoint, api_key, model, endpoint_provider, "WARNING")
    cmd = Task(f"Please rewrite the kubectl command so that the action (ie: get, patch, etc) is directly after the kubectl keyword and the namespace is at the end. For instance, we want 'kubectl get pod -n <namespace>'.  The command to update: `{cmd}`\nOnly answer with the updated command and nothing else (no quotes either). Just the updated raw kubectl command with its new parameters correctly ordered.", agent).solve().content
    split_cmd = cmd.split(" ")
    LoggerManager.set_log_level(log_level)

  if split_cmd[1] == "watch": # Ca ca va poser pb. Car la boucle de validation va quand même réessayer. Sauf si le LLM peut shit sur sleep dans le retry de yacana ?
    raise ToolError("Verb `watch` is blocked because this particular command doesn't exit. To wait for some specific time use the sleep tool.")

  # Limiting tail output length so the context size stays manageable
  if split_cmd[1] == "logs" and "--tail" not in cmd:
    endpoint, api_key, model, endpoint_provider, log_level = get_config_from_env()
    agent = init_agent(endpoint, api_key, model, endpoint_provider, "WARNING")
    cmd = Task(f"Please add the missing --tail=100 in this kubectl command: `{cmd}`\nOnly answer with the updated command and nothing else (no quotes either). Just the updated raw kubectl command with its new tail parameter.", agent).solve().content
    split_cmd = cmd.split(" ")
    LoggerManager.set_log_level(log_level)

  # If it's not a 'observation' cmd then ask user for validation
  if split_cmd[1] != "get" and split_cmd[1] != "describe" and split_cmd[1] != "logs":
    confirm_exec("Exec command ?")
  try:
    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, timeout=20, universal_newlines=True)
    if config.g_print_tool_output:
      print(f"{ANSI_CYAN}{output}{ANSI_RESET}")
    return output
  except subprocess.CalledProcessError as e:
    raise ToolError(repr(e.output))
  except subprocess.TimeoutExpired as e:
    return f"Command timed out after {e.timeout}s: {cmd}"


def ask_question_to_admin(question: str):
  """
  Prompts the user with a question from the LLM
  """
  if not isinstance(question, str):
    raise ToolError(f"Tool argument `question` MUST be of type string. Got {type(question)}.")
  return questionary.text(question).ask()


def sleep(seconds_to_sleep: int):
  """
  Sleeps for a period of time so the LLM doesn't have to spam needlessly
  """
  if not isinstance(seconds_to_sleep, int):
    raise ToolError(f"Tool argument `question` MUST be of type int. Got {type(seconds_to_sleep)}.")
  if config.g_print_tool_output:
    print(f"Sleeping {seconds_to_sleep} seconds.")
  time.sleep(seconds_to_sleep)
