print("Booting...")

from yacana import OllamaAgent, OpenAiAgent, Task, Tool, ToolType, Message, GenericMessage, OllamaModelSettings, OpenAiModelSettings, LoggerManager, ToolError, MaxToolErrorIter, MessageRole
import questionary
import time, subprocess, os
from enum import Enum


class CustomTool(Enum):
    KUBECTL = 1
    ASK_QUESTION = 2
    SLEEP = 3
    SOLVED_TASK = 4


g_used_tools: list[CustomTool] = []

def get_config_from_env():
  """
  Validating credentials are present
  """
  inter = False
  if (endpoint := os.getenv("GNO6_ENDPOINT", None)) is None:
    endpoint, inter = questionary.text("What's the LLM endpoint URL (should end with /v1) ?").ask(), True

  if (api_key := os.getenv("GNO6_API_KEY", None)) is None:
    api_key, inter = questionary.password("What's the api key ?").ask(), True

  if (model := os.getenv("GNO6_MODEL", None)) is None:
    model, inter = questionary.text("What's the model name ?").ask(), True

  if (provider := os.getenv("GNO6_PROVIDER", None)) is None:
    provider, inter = questionary.select("What's the provider type", choices=["openai", "ollama"],).ask(), True

  if (log_level := os.getenv("GNO6_LOG_LEVEL", None)) is None:
    log_level, inter = questionary.select("What log level do you want (choose INFO if unsure) ?", choices=["DEBUG", "INFO", "WARNING"],).ask(), True

  if inter is True:
    print(f"""Set these ENV variables so you don't have to do this again:
export GNO6_ENDPOINT={endpoint}
export GNO6_API_KEY={api_key}
export GNO6_MODEL={model}
export GNO6_PROVIDER={provider}
export GNO6_LOG_LEVEL={log_level}
""")
  return (endpoint, api_key, model, provider, log_level)


class TaskIsSolved(Exception):
  """
  Exception raised when the LLM thinks that the current task is solved.
  """

  def __init__(self, message):
    self.message = message
    super().__init__(self.message)

############################
# Tools for the LLM to use #
############################

def call_kubectl_cmd(cmd: str):
  """
  Executes a kubectl command
  """
  g_used_tools.append(CustomTool.KUBECTL)
  print(f"Command to execute\n```\n{cmd}\n```")
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
    while True:
      confirmed: bool = questionary.confirm("Exec command ?").ask()
      if confirmed:
        break
      elif not confirmed:
        reason: str = questionary.text("Reason to give the LLM why you said no.").ask()
        raise ToolError(f"kubectl command was denied by the cluster admin with the following reason : {reason}")
  try:
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, timeout=20, universal_newlines=True)
  except subprocess.CalledProcessError as e:
    raise ToolError(repr(e.output))


def ask_question_to_admin(question: str):
  """
  Prompts the user with a question from the LLM
  """
  g_used_tools.append(CustomTool.ASK_QUESTION)
  if not isinstance(question, str):
    raise ToolError(f"Tool argument `question` MUST be of type string. Got {type(question)}.")
  return questionary.text(question).ask()


def sleep(seconds_to_sleep: int):
  """
  Sleeps for a period of time so the LLM doesn't have to spam needlessly
  """
  g_used_tools.append(CustomTool.SLEEP)
  if not isinstance(seconds_to_sleep, int):
    raise ToolError(f"Tool argument `question` MUST be of type int. Got {type(seconds_to_sleep)}.")
  time.sleep(seconds_to_sleep)


def mission_accomplished():
  """
  When the task is done, ends the current workflow.
  """
  g_used_tools.append(CustomTool.SOLVED_TASK)
  raise TaskIsSolved("LLM thinks it solved the initial task")


#################################
# Initializing tools and agents #
#################################

def init_tools():
  kubectl_tool = Tool("exec", "Executes a kubectl command and return the output. The string must start by 'kubectl' and be a valid kubectl command.", call_kubectl_cmd, optional=True)
  ask_question_to_admin_tool = Tool("human_in_the_loop", "Asks the cluster admin a question and returns his answer.", ask_question_to_admin)
  sleep_tool = Tool("sleep", "Waits for a specified period of time. Useful to wait for kubernetes resource to update.", sleep) # tool_type=ToolType.OPENAI
  task_is_solved_tool = Tool("task_is_solved", "Call this tool when you think the initial task is solved. You will be given a completely new task after calling this.", mission_accomplished, optional=True)
  return (kubectl_tool, ask_question_to_admin_tool, sleep_tool, task_is_solved_tool)


def init_agent(endpoint: str, api_key: str, model: str, type: str, logging_level=None) -> None:
  system_prompt="""You are a helpful AI assistant expert on kubernetes and kubectl. You job is to fulfill a kubernetes related task given by the cluster admin. To help you fulfill the task you have access to a kubectl tool letting you interact with the cluter. Use it wisely. When debbuging, always follow this approch:

# PLANIFICATION PHASE
* Always plan your tasks in advance.

# SCOUTING PHASE
* Extensively list resources that might help using `kubectl get <resource-kind>` -n <namespace>.
* Always look at YAML resources configuration using `kubectl get <resource-kind> <resource-name> -n <namespce> -o yaml`
* Read last pods logs using `kubectl logs <resource-name> --tail=200 -n <namespace>`
* Do not list the whole cluster as YAML because your context is limited. Choose what resource specificaly interests you.

# ANALYSING PHASE
* Think of what information you gathered and update your plan accordingly

# TAKING ACTION PHASE
* Now that you know how to fulfill the user's request take action.
* Use kubectl commands to update resources. You can use verbs like patch, scale, rollout etc.
* Use `kubectl explain` when getting contradicting or no result commands.

When requiring more information about an issue or needing help, you can ask question to the cluster admin using the ask_question tool. Don't do everything all at once. Do one thing at a time. Decompose actions and work step by step. When calling the kubectl tool only provide one command at a time. You will have many opportunities to execute kubectl commands so don't rush.
"""
  if type == "openai":
    agent = OpenAiAgent("AI assistant", model, api_token=api_key, endpoint=endpoint)
  elif type == "ollama":
    agent = OllamaAgent("AI assistant", model, endpoint=endpoint, system_prompt=system_prompt)
  else:
    raise ValueError("Agent type can either be `openai` or `ollama`")

  LoggerManager.set_log_level(logging_level)
  return agent


def compact_history(agent):
  recap: str = Task("""Let's recap all steps that you went through and their associated results. To do so create an ordered list following this format:
* 1) <Subtask title>
Command: `<kubectl command that was done>`
Relevant ouput:
```
<Meaningful output from the command. Only keep what is relevant.>
```
Conclusion: <Conclusions from the output>

---

Example when looking for a resource:
* 1) Looking for target pod.
Command `kubectl get pod -n mynamespace`
Relevant output:
```
NAME        READY   STATUS    RESTARTS   AGE
my-pod      1/1     Running   0          12d
```
Conclusion: Pod has been found in namespace mynamespace and is running.

---

Example with a `kubectl logs`:
* 1) Searching for root cause inside logs of pod my-pod.
Command: `kubectl logs my-pod -n mynamespace`
Meaningful output:
```
14:00-Booting app
14:00-OutOfMemory exception
```
Conclusion: Logs show that the Pod may be running out of memory.

---

Final instructions: Do not make things up. Ground your answer based on this conversation.
""", agent).solve().content
  tagged_messages = agent.history.get_messages_by_tags("kubectl")
  for tagged_msg in tagged_messages:
    agent.history.delete_message(tagged_msg)
  agent.history.pretty_print()
  agent.history.add_message(Message(MessageRole.USER, "Let's recap all operations that have already be done.", ["compact"]))
  agent.history.add_message(Message(MessageRole.ASSISTANT, recap, ["compact"]))
  print("------------------------------")
  agent.history.pretty_print()

###################
# Main logic loop #
###################

def main():
  endpoint, api_key, model, endpoint_provider, log_level = get_config_from_env()
  kubectl_tool, ask_question_tool, sleep_tool, task_is_solved_tool = init_tools()

  while True:
    init: bool = True
    main_agent = init_agent(endpoint, api_key, model, endpoint_provider, log_level)
    user_query: str = questionary.text("How can I assist you with your cluster today ?").ask()
    if user_query is None:
      return 0

    try:
      while True:
        prompt: str = "Do you need to exec another command ?" if init is False else f"You have received a task from the kubernetes cluster admin. <task>{user_query}</task>. Fulfill the admin's task using the tools at your disposition. Start with the planification phase then take action."
        Task(prompt, main_agent, tools=[kubectl_tool, sleep_tool], tags=["kubectl"]).solve()
        init = False

        Task("Do you have any questions to the cluster admin ? If you can continue working autonomously then cary on. Else use the tool to ask a question.", main_agent, tools=[ask_question_tool]).solve()
        Task("In your opinion, is the initial task solved or should you keep working ?", main_agent, tools=[task_is_solved_tool], forget=True).solve()

        #print("BBBBBBBBBBBBBBBBBBBBBBBBBBLLLLLLLLLLLLLLLAAAAHHH", main_agent.history.get_token_count())
        if main_agent.history.get_token_count() > 1000:
          compact_history(main_agent)

    except TaskIsSolved:
      answer: bool = questionary.confirm("LLM thinks that the original task is solved.")
      if answer is True:
        continue
      else:
        pass

main()
