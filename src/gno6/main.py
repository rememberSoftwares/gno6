if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "gno6"

print(r"""
  ______   __    __   ______    ______  
 /      \ |  \  |  \ /      \  /      \ 
|  $$$$$$\| $$\ | $$|  $$$$$$\|  $$$$$$\ 
| $$ __\$$| $$$\| $$| $$  | $$| $$___\$$ 
| $$|    \| $$$$\ $$| $$  | $$| $$    \ 
| $$ \$$$$| $$\$$ $$| $$  | $$| $$$$$$$\ 
| $$__| $$| $$ \$$$$| $$__/ $$| $$__/ $$ 
 \$$    $$| $$  \$$$ \$$    $$ \$$    $$ 
  \$$$$$$  \$$   \$$  \$$$$$$   \$$$$$$ 
                                        
                                        
                                        
""")
print("Powered by Yacana (https://remembersoftwares.github.io/yacana)")
print("alpha2.1")
print("Booting...")

from yacana import OllamaAgent, OpenAiAgent, Task, Tool, ToolType, Message, GenericMessage, OllamaModelSettings, OpenAiModelSettings, LoggerManager, ToolError, MaxToolErrorIter, MessageRole
import questionary
import time, subprocess, os, uuid
from pathlib import Path
from enum import Enum
import sys
from .llm_fs_tools import (FilesystemToolbox, ToolError)
from .kubectl_tools import *
from . import config

sys.stdout.write("\033[F")
sys.stdout.write("\033[F")
sys.stdout.write("\033[F")
sys.stdout.write("\033[K")

class CustomTool(Enum):
    KUBECTL = 1
    ASK_QUESTION = 2
    SLEEP = 3
    SOLVED_TASK = 4


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
    log_level, inter = questionary.select("What log level do you want ?", choices=["DEFAULT", "INFO"]).ask(), True

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

def mission_accomplished(final_report: str):
  """
  When the task is done, ends the current workflow.
  """
  print(f"{ANSI_GREEN}{final_report}{ANSI_RESET}")
  raise TaskIsSolved("LLM thinks it solved the initial task")


#################################
# Initializing tools and agents #
#################################

def init_tools():
  kubectl_exec_tool = Tool("kubectl_exec", "Executes a kubectl command and return the output. The string must start by 'kubectl' and be a valid kubectl command.", call_kubectl_cmd, max_custom_error=70, max_call_error=70, optional=True, tool_type=ToolType.OPENAI)
  helm_exec_tool = Tool("helm_exec", "Executes a helm command and return the output. The string must start by 'helm' and be a valid helm command.", call_helm_cmd, max_custom_error=70, max_call_error=70, optional=True, tool_type=ToolType.OPENAI)
  ask_question_to_admin_tool = Tool("human_in_the_loop", "Asks the cluster admin a question and returns his answer.", ask_question_to_admin, max_custom_error=70, max_call_error=70, tool_type=ToolType.OPENAI, optional=True)
  sleep_tool = Tool("sleep", "Waits for a specified period of time. Useful to wait for kubernetes resource to update.", sleep, max_custom_error=70, max_call_error=70, tool_type=ToolType.OPENAI, optional=True) # tool_type=ToolType.OPENAI
  task_is_solved_tool = Tool("task_is_solved", "Call this tool when you think the initial task is solved. If you do call this tool then give your final report to the Kubernetes admin as tool parameter. Use the report to answer the initial task that you were assigned and explain your actions. You will be given a completely new task after calling this tool.", mission_accomplished, max_custom_error=70, max_call_error=70, optional=True, tool_type=ToolType.OPENAI)

  tools = FilesystemToolbox(workspace_root=Path(".").resolve())
  list_files_tool = Tool("list_files","List files under `path`. Returns structured dict.\n"
        ":param path: directory path relative to workspace_root\n"
        ":param recursive: whether to recurse\n"
        ":param show_line_count: if True, include the number of lines in each file (text files; binary skipped)",
        tools.list_files, max_custom_error=70, max_call_error=70, optional=True, tool_type=ToolType.OPENAI)

  read_file_tool = Tool("read_file", "Read file lines using 1-based inclusive indexing.\n"
        "If both start_line and end_line are None -> return full file.\n"
        "Raises ToolError if OOB.",
        tools.read_file, max_custom_error=70, max_call_error=70, optional=True, tool_type=ToolType.OPENAI)

  write_file_tool = Tool("write_file", "Create or overwrite a file.\n"
        ":param path: path relative to workspace_root\n"
        ":param content: full file content (string)\n"
        ":param overwrite: allow overwrite if file exists",
        tools.write_file, max_custom_error=70, max_call_error=70, optional=True, tool_type=ToolType.OPENAI)

  edit_file_tool = Tool("edit_file", "Replace lines [start_line, end_line] (1-based inclusive) with replacement text.\n"
        "Returns metadata and a colorized diff (if modified snippet < 100 lines).\n"
        "Raises ToolError for OOB or missing file.\n",
        tools.edit_file, max_custom_error=70, max_call_error=70, optional=True, tool_type=ToolType.OPENAI)

  search_in_files_tool = Tool("search_in_files", "Search for `pattern` inside files under path. Returns list of matches:\n"
        '{ "file": "path", "line_no": n, "line": "...", "match": "..." }\n'
        ":param pattern: string or regex\n"
        ":param path: directory/file path relative to workspace_root\n"
        ":param max_results: stop after this many matches\n"
        ":param use_regex: if True compile pattern as regex (re.I by default if pattern looks case-insensitive)",
        tools.search_in_files, max_custom_error=70, max_call_error=70, optional=True, tool_type=ToolType.OPENAI)

  exec_script_tool = Tool("exec_script", "Execute a script at path. If background=True, start process and return PID and log paths; does not wait.\n"
        "If background=False, run synchronously and return exit code, stdout and stderr.\n"
        "Security:\n"
        "  - The script path must be inside workspace_root.\n"
        "  - 'shell' lets you run via shell; default False (recommended).",
        tools.exec_script, max_custom_error=70, max_call_error=70, optional=True, tool_type=ToolType.OPENAI)

  print("#################")
  print(edit_file_tool._openai_function_schema)
  print(edit_file_tool._function_prototype)
  print(str(edit_file_tool._function_args))
  print("||||||||||||||||||||")

  return (kubectl_exec_tool, helm_exec_tool, ask_question_to_admin_tool, sleep_tool, task_is_solved_tool, list_files_tool, read_file_tool, write_file_tool, edit_file_tool, search_in_files_tool, exec_script_tool)


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

General guidelines:
* When requiring more information about an issue or needing help, you can ask question to the cluster admin using the ask_question tool. Don't do everything all at once. Do one thing at a time. Decompose actions and work step by step. When calling the kubectl tool only provide one command at a time. You will have many opportunities to execute kubectl commands so don't rush.
* When editing YAML files:  
- preserve existing indentation  
- never change indentation outside the edited lines  
- match the indentation level of surrounding lines  
"""
  if type == "openai":
    agent = OpenAiAgent("AI assistant", model, api_token=api_key, endpoint=endpoint, system_prompt=system_prompt)
  elif type == "ollama":
    agent = OllamaAgent("AI assistant", model, endpoint=endpoint, system_prompt=system_prompt)
  else:
    raise ValueError("Agent type can either be `openai` or `ollama`")

  logging_level = "WARNING" if logging_level == "DEFAULT" else logging_level
  LoggerManager.set_log_level(logging_level)
  config.g_print_tool_output = True if logging_level == "WARNING" else False
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
  kubectl_exec_tool, helm_exec_tool, ask_question_tool, sleep_tool, task_is_solved_tool, list_files_tool, read_file_tool, write_file_tool, edit_file_tool, search_in_files, exec_script_tool = init_tools()

  while True:
    init: bool = True
    main_agent = init_agent(endpoint, api_key, model, endpoint_provider, log_level)
    user_query: str = questionary.text("How may I help with your cluster ?").ask()
    if user_query is None:
      return 0

    Task("We want to make sure that the given task has a clear final objective. How do you know that you have achieved/finished the task ? It has to be clear ! So, if you have a question, you can ask it using a tool. On the other hand, if the original task is clear and you understand what is expected from you then then we're good and you'll be able to start working next.", main_agent, tools=[ask_question_tool])

    try:
      while True:
        uid: str = str(uuid.uuid4())
        prompt: str = "Do you need to use a tool" if init is False else f"You have received a task from the kubernetes cluster admin. <task>{user_query}</task>. Fulfill the admin's task using the tools at your disposition. Start with the planification phase then take action."
        Task(prompt, main_agent, tools=[kubectl_exec_tool, helm_exec_tool, sleep_tool, ask_question_tool, list_files_tool, read_file_tool, write_file_tool, edit_file_tool, search_in_files], tags=["kubectl", uid]).solve()
        init = False

        #Task("Do you have any questions to the cluster admin ? If you can continue working autonomously then cary on. Else use the tool to ask a question.", main_agent, tools=[ask_question_tool], tags=[uid]).solve()
        Task("In your opinion, is the initial task solved or should you keep working ?", main_agent, tools=[task_is_solved_tool], tags=[uid]).solve()

        #Task("", main_agent, tags=[uid])

        #print("Token count", main_agent.history.get_token_count())
        #if main_agent.history.get_token_count() > 10000:
        #  compact_history(main_agent)

    except TaskIsSolved:
      answer: bool = questionary.confirm("LLM thinks that the original task is solved.")
      if answer is True:
        continue
      else:
        pass


if __name__ == "__main__":
    main()
