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
print("alpha2.2")
print("Booting...")

from typing import Tuple

from yacana import (
    OllamaAgent,
    OpenAiAgent,
    GenericAgent,
    Task,
    Tool,
    ToolType,
    Message,
    GenericMessage,
    OllamaModelSettings,
    OpenAiModelSettings,
    LoggerManager,
    ToolError,
    MaxToolErrorIter,
    MessageRole,
    Mcp,
)
import questionary
import time, subprocess, os, uuid, json
from pathlib import Path
from enum import Enum
import sys
from datetime import datetime
from .llm_fs_tools import FilesystemToolbox, ToolError
from .kubectl_tools import *
from .gitlab_tools import get_gitlab_tools, load_gitlab_config, save_gitlab_config
from .jira_tools import get_jira_tools, load_jira_config, save_jira_config
from . import config

sys.stdout.write("\033[F")
sys.stdout.write("\033[F")
sys.stdout.write("\033[F")
sys.stdout.write("\033[K")
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
        endpoint, inter = (
            questionary.text(
                "What's the LLM endpoint URL (should end with /v1) ?"
            ).ask(),
            True,
        )

    if (api_key := os.getenv("GNO6_API_KEY", None)) is None:
        api_key, inter = questionary.password("What's the api key ?").ask(), True

    if (model := os.getenv("GNO6_MODEL", None)) is None:
        model, inter = questionary.text("What's the model name ?").ask(), True

    if (provider := os.getenv("GNO6_PROVIDER", None)) is None:
        provider, inter = (
            questionary.select(
                "What's the provider type",
                choices=["openai", "ollama"],
            ).ask(),
            True,
        )

    if (log_level := os.getenv("GNO6_LOG_LEVEL", None)) is None:
        log_level, inter = (
            questionary.select(
                "What log level do you want ?", choices=["DEFAULT", "INFO"]
            ).ask(),
            True,
        )

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
    kubectl_exec_tool = Tool(
        "kubectl_exec",
        "Executes a kubectl command and return the output. The string must start by 'kubectl' and be a valid kubectl command.",
        call_kubectl_cmd,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )
    helm_exec_tool = Tool(
        "helm_exec",
        "Executes a helm command and return the output. The string must start by 'helm' and be a valid helm command.",
        call_helm_cmd,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )
    git_exec_tool = Tool(
        "git_exec",
        "Executes a git command and return the output. The string must start by 'git' and be a valid git command.",
        call_git_cmd,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )
    ask_question_to_admin_tool = Tool(
        "human_in_the_loop",
        "Asks the cluster admin a question and returns his answer.",
        ask_question_to_admin,
        max_custom_error=70,
        max_call_error=70,
        tool_type=ToolType.OPENAI,
        optional=True,
    )
    sleep_tool = Tool(
        "sleep",
        "Waits for a specified period of time. Useful to wait for kubernetes resource to update.",
        sleep,
        max_custom_error=70,
        max_call_error=70,
        tool_type=ToolType.OPENAI,
        optional=True,
    )  # tool_type=ToolType.OPENAI
    task_is_solved_tool = Tool(
        "task_is_solved",
        "Call this tool when you think the initial task is solved. If you do call this tool then give your final report to the Kubernetes admin as tool parameter. Use the report to answer the initial task that you were assigned and explain your actions. You will be given a completely new task after calling this tool.",
        mission_accomplished,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )

    tools = FilesystemToolbox(workspace_root=Path(".").resolve())
    list_files_tool = Tool(
        "list_files",
        "List files under `path`. Returns structured dict.\n"
        ":param path: directory path relative to workspace_root\n"
        ":param recursive: whether to recurse\n"
        ":param show_line_count: if True, include the number of lines in each file (text files; binary skipped)",
        tools.list_files,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )

    read_file_tool = Tool(
        "read_file",
        "Read file lines using 1-based inclusive indexing.\n"
        "If both start_line and end_line are None -> return full file.\n"
        "Raises ToolError if OOB.",
        tools.read_file,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )

    write_file_tool = Tool(
        "write_file",
        "Create or overwrite a file.\n"
        ":param path: path relative to workspace_root\n"
        ":param content: full file content (string)\n"
        ":param overwrite: allow overwrite if file exists",
        tools.write_file,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )

    edit_file_tool = Tool(
        "edit_file",
        "Replace lines [start_line, end_line] (1-based inclusive) with replacement text.\n"
        "Returns metadata and a colorized diff (if modified snippet < 100 lines).\n"
        "Raises ToolError for OOB or missing file.\n",
        tools.edit_file,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )

    search_in_files_tool = Tool(
        "search_in_files",
        "Search for `pattern` inside files under path. Returns list of matches:\n"
        '{ "file": "path", "line_no": n, "line": "...", "match": "..." }\n'
        ":param pattern: string or regex\n"
        ":param path: directory/file path relative to workspace_root\n"
        ":param max_results: stop after this many matches\n"
        ":param use_regex: if True compile pattern as regex (re.I by default if pattern looks case-insensitive)",
        tools.search_in_files,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )

    exec_script_tool = Tool(
        "exec_script",
        "Execute a script at path. If background=True, start process and return PID and log paths; does not wait.\n"
        "If background=False, run synchronously and return exit code, stdout and stderr.\n"
        "Security:\n"
        "  - The script path must be inside workspace_root.\n"
        "  - 'shell' lets you run via shell; default False (recommended).",
        tools.exec_script,
        max_custom_error=70,
        max_call_error=70,
        optional=True,
        tool_type=ToolType.OPENAI,
    )

    return (
        kubectl_exec_tool,
        helm_exec_tool,
        git_exec_tool,
        ask_question_to_admin_tool,
        sleep_tool,
        task_is_solved_tool,
        list_files_tool,
        read_file_tool,
        write_file_tool,
        edit_file_tool,
        search_in_files_tool,
        exec_script_tool,
    )


def init_agent(
    endpoint: str, api_key: str, model: str, type: str, logging_level=None
) -> GenericAgent:
    system_prompt = """You are a helpful AI DEVOPS assistant expert on kubernetes. Your job is to fulfill a DEVOPS related task given by the Kubernetes cluster admin. To help you fulfill the task you have access to a list of tools letting you interact with k8s cluters, Gitlab or Jira. Use them wisely. When debbuging, always follow this approch:

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
        agent = OpenAiAgent(
            "AI assistant",
            model,
            api_token=api_key,
            endpoint=endpoint,
            system_prompt=system_prompt,
        )
    elif type == "ollama":
        agent = OllamaAgent(
            "AI assistant", model, endpoint=endpoint, system_prompt=system_prompt
        )
    else:
        raise ValueError("Agent type can either be `openai` or `ollama`")

    logging_level = "WARNING" if logging_level == "DEFAULT" else logging_level
    LoggerManager.set_log_level(logging_level)
    config.g_print_tool_output = True if logging_level == "WARNING" else False
    return agent


def load_previous_conversations() -> None | str:
    conv_dir = Path.home() / ".cache" / "gno6" / "conversations"

    if not conv_dir.exists():
        return None

    json_files = list(conv_dir.glob("*.json"))
    if not json_files:
        return None

    choices = []
    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
            title = data.get("title", "Untitled")
            timestamp = json_file.stem
            try:
                date_str = datetime.fromtimestamp(int(timestamp)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                date_str = timestamp
            choices.append(f"{date_str} : {title}")
        except (json.JSONDecodeError, KeyError):
            continue

    if not choices:
        return None

    choices.sort(reverse=True)

    selected = questionary.select("Select a conversation:", choices=choices).ask()
    if selected is None:
        return None

    selected_index = choices.index(selected)
    selected_file = json_files[json_files.__len__() - 1 - selected_index]

    action = questionary.select(
        "What do you want to do?", choices=["Load", "Delete"]
    ).ask()
    if action is None:
        return None

    if action == "Delete":
        os.remove(selected_file)
        return None

    with open(selected_file, "r") as f:
        data = json.load(f)
    return json.dumps(data["content"])


def save_conversation(agent: GenericAgent):
    title = (
        Task(
            "Based on what was intialy asked and what you did, create a one short sentence sumurrizing the main topic of this conversation. This will be used as conversation title. Answer only with the title.",
            agent,
            forget=True,
        )
        .solve()
        .content
    )
    raw: str = agent.export_to_raw(strip_api_token=True)

    # Chemin du fichier
    file_path = (
        Path.home() / ".cache" / "gno6" / "conversations" / f"{int(time.time())}.json"
    )

    # Créer les répertoires parents s'ils n'existent pas
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Écrire le fichier
    with open(file_path, "w") as f:
        json.dump({"title": title, "content": json.loads(raw)}, f, indent=4)


def load_agent(command: str) -> Tuple[bool, GenericAgent]:
    endpoint, api_key, model, endpoint_provider, log_level = get_config_from_env()

    if command.startswith("/history"):
        conversation_history = load_previous_conversations()
        if conversation_history is not None:
            agent_from_state = GenericAgent.import_from_raw(conversation_history)
            agent_from_state.endpoint = endpoint
            agent_from_state.api_token = api_key
            agent_from_state.model = model
            return True, agent_from_state
    return False, None


def manage_mcp_connections(command: str) -> bool:
    if command.startswith("/mcp"):
        choice = questionary.select(
            "Add or delete MCP URL ?", choices=["Add", "Delete", "Activate/Deactivate"]
        ).ask()
        if choice is None:
            os._exit(0)

        mcp_config_path = Path.home() / ".config" / "gno6" / "mcp.json"
        mcp_config_path.parent.mkdir(parents=True, exist_ok=True)

        if mcp_config_path.exists():
            with open(mcp_config_path, "r") as f:
                mcp_urls = json.load(f).get("urls", [])
        else:
            mcp_urls = []

        if choice == "Add":
            mcp_url = questionary.text("What's the MCP URL ?").ask()
            if mcp_url is None:
                os._exit(0)
            existing_urls = [
                entry.get("url") if isinstance(entry, dict) else entry
                for entry in mcp_urls
            ]
            if mcp_url not in existing_urls:
                mcp_urls.append({"url": mcp_url, "active": True})
                with open(mcp_config_path, "w") as f:
                    json.dump({"urls": mcp_urls}, f, indent=2)
                print(f"MCP URL added: {mcp_url}")
        elif choice == "Delete":
            if not mcp_urls:
                print("No MCP URLs configured.")
                return True
            choices = []
            for entry in mcp_urls:
                if isinstance(entry, dict):
                    url = entry.get("url", "")
                    active = entry.get("active", True)
                    status = "[Active]" if active else "[Unactive]"
                    choices.append(f"{status} {url}")
                else:
                    choices.append(f"[Active] {entry}")
            selected = questionary.select(
                "Select MCP URL to delete:", choices=choices
            ).ask()
            if selected is None:
                os._exit(0)
            selected_url = selected.split("] ", 1)[-1]
            for i, entry in enumerate(mcp_urls):
                url = entry.get("url") if isinstance(entry, dict) else entry
                if url == selected_url:
                    mcp_urls.pop(i)
                    break
            with open(mcp_config_path, "w") as f:
                json.dump({"urls": mcp_urls}, f, indent=2)
            print(f"MCP URL deleted: {selected_url}")
        elif choice == "Activate/Deactivate":
            if not mcp_urls:
                print("No MCP URLs configured.")
                return True
            choices = []
            for entry in mcp_urls:
                if isinstance(entry, dict):
                    url = entry.get("url", "")
                    active = entry.get("active", True)
                    status = "[Active]" if active else "[Unactive]"
                    choices.append(f"{status} {url}")
                else:
                    choices.append(f"[Active] {entry}")
            selected = questionary.select(
                "Select MCP URL to toggle:", choices=choices
            ).ask()
            if selected is None:
                os._exit(0)
            selected_url = selected.split("] ", 1)[-1]
            for i, entry in enumerate(mcp_urls):
                if isinstance(entry, dict):
                    if entry.get("url") == selected_url:
                        mcp_urls[i]["active"] = not entry.get("active", True)
                        break
                elif entry == selected_url:
                    mcp_urls[i] = {"url": entry, "active": False}
                    break
            with open(mcp_config_path, "w") as f:
                json.dump({"urls": mcp_urls}, f, indent=2)
            print(selected_url)
        return True
    return False


def manage_gitlab_connections(command: str) -> bool:
    if command.startswith("/gitlab"):
        choice = questionary.select(
            "Add, delete or toggle GitLab instance ?",
            choices=["Add", "Delete", "Activate/Deactivate"],
        ).ask()
        if choice is None:
            os._exit(0)

        instances = load_gitlab_config()

        if choice == "Add":
            alias = questionary.text(
                "GitLab instance alias (unique identifier) ?"
            ).ask()
            if alias is None:
                os._exit(0)
            url = questionary.text("GitLab URL (e.g. https://gitlab.com) ?").ask()
            if url is None:
                os._exit(0)
            token = questionary.password("Personal access token ?").ask()
            if token is None:
                os._exit(0)
            project_path = questionary.text(
                "Project path (e.g. namespace/repo) ?"
            ).ask()
            if project_path is None:
                os._exit(0)
            ssl_verify = questionary.confirm("Verify SSL ?", default=True).ask()
            if ssl_verify is None:
                os._exit(0)

            existing_aliases = [
                inst.get("alias") if isinstance(inst, dict) else inst
                for inst in instances
            ]
            if alias in existing_aliases:
                print(f"GitLab '{alias}' already exists.")
                return True

            instances.append(
                {
                    "alias": alias,
                    "url": url,
                    "token": token,
                    "project_path": project_path,
                    "ssl_verify": ssl_verify,
                    "active": True,
                }
            )
            save_gitlab_config(instances)
            print(f"GitLab '{alias}' added.")
        elif choice == "Delete":
            if not instances:
                print("No GitLab instances configured.")
                return True
            choices = []
            for entry in instances:
                if isinstance(entry, dict):
                    alias = entry.get("alias", "")
                    active = entry.get("active", True)
                    status = "[Active]" if active else "[Inactive]"
                    choices.append(f"{status} {alias}")
                else:
                    choices.append(f"[Active] {entry}")
            selected = questionary.select(
                "Select GitLab instance to delete:", choices=choices
            ).ask()
            if selected is None:
                os._exit(0)
            selected_alias = selected.split("] ", 1)[-1]
            for i, entry in enumerate(instances):
                alias = entry.get("alias") if isinstance(entry, dict) else entry
                if alias == selected_alias:
                    instances.pop(i)
                    break
            save_gitlab_config(instances)
            print(f"GitLab '{selected_alias}' deleted.")
        elif choice == "Activate/Deactivate":
            if not instances:
                print("No GitLab instances configured.")
                return True
            choices = []
            for entry in instances:
                if isinstance(entry, dict):
                    alias = entry.get("alias", "")
                    active = entry.get("active", True)
                    status = "[Active]" if active else "[Inactive]"
                    choices.append(f"{status} {alias}")
                else:
                    choices.append(f"[Active] {entry}")
            selected = questionary.select(
                "Select GitLab instance to toggle:", choices=choices
            ).ask()
            if selected is None:
                os._exit(0)
            selected_alias = selected.split("] ", 1)[-1]
            new_status = "deactivated"
            for i, entry in enumerate(instances):
                if isinstance(entry, dict):
                    if entry.get("alias") == selected_alias:
                        instances[i]["active"] = not entry.get("active", True)
                        new_status = (
                            "activated" if instances[i]["active"] else "deactivated"
                        )
                        break
                elif entry == selected_alias:
                    instances[i] = {"alias": entry, "active": False}
                    break
            save_gitlab_config(instances)
            print(f"GitLab '{selected_alias}' {new_status}.")
        return True
    return False


def manage_jira_connections(command: str) -> bool:
    if command.startswith("/jira"):
        choice = questionary.select(
            "Add, delete or toggle Jira instance ?",
            choices=["Add", "Delete", "Activate/Deactivate"],
        ).ask()
        if choice is None:
            os._exit(0)

        instances = load_jira_config()

        if choice == "Add":
            alias = questionary.text("Jira instance alias (unique identifier) ?").ask()
            if alias is None:
                os._exit(0)
            url = questionary.text(
                "Jira URL (e.g. https://company.atlassian.net) ?"
            ).ask()
            if url is None:
                os._exit(0)
            email = questionary.text("Email ?").ask()
            if email is None:
                os._exit(0)
            api_token = questionary.password("API token ?").ask()
            if api_token is None:
                os._exit(0)
            verify_ssl = questionary.confirm("Verify SSL ?", default=True).ask()
            if verify_ssl is None:
                os._exit(0)

            existing_aliases = [
                inst.get("alias") if isinstance(inst, dict) else inst
                for inst in instances
            ]
            if alias in existing_aliases:
                print(f"Jira '{alias}' already exists.")
                return True

            instances.append(
                {
                    "alias": alias,
                    "url": url,
                    "email": email,
                    "api_token": api_token,
                    "verify_ssl": verify_ssl,
                    "active": True,
                }
            )
            save_jira_config(instances)
            print(f"Jira '{alias}' added.")
        elif choice == "Delete":
            if not instances:
                print("No Jira instances configured.")
                return True
            choices = []
            for entry in instances:
                if isinstance(entry, dict):
                    alias = entry.get("alias", "")
                    active = entry.get("active", True)
                    status = "[Active]" if active else "[Inactive]"
                    choices.append(f"{status} {alias}")
                else:
                    choices.append(f"[Active] {entry}")
            selected = questionary.select(
                "Select Jira instance to delete:", choices=choices
            ).ask()
            if selected is None:
                os._exit(0)
            selected_alias = selected.split("] ", 1)[-1]
            for i, entry in enumerate(instances):
                alias = entry.get("alias") if isinstance(entry, dict) else entry
                if alias == selected_alias:
                    instances.pop(i)
                    break
            save_jira_config(instances)
            print(f"Jira '{selected_alias}' deleted.")
        elif choice == "Activate/Deactivate":
            if not instances:
                print("No Jira instances configured.")
                return True
            choices = []
            for entry in instances:
                if isinstance(entry, dict):
                    alias = entry.get("alias", "")
                    active = entry.get("active", True)
                    status = "[Active]" if active else "[Inactive]"
                    choices.append(f"{status} {alias}")
                else:
                    choices.append(f"[Active] {entry}")
            selected = questionary.select(
                "Select Jira instance to toggle:", choices=choices
            ).ask()
            if selected is None:
                os._exit(0)
            selected_alias = selected.split("] ", 1)[-1]
            new_status = "deactivated"
            for i, entry in enumerate(instances):
                if isinstance(entry, dict):
                    if entry.get("alias") == selected_alias:
                        instances[i]["active"] = not entry.get("active", True)
                        new_status = (
                            "activated" if instances[i]["active"] else "deactivated"
                        )
                        break
                elif entry == selected_alias:
                    instances[i] = {"alias": entry, "active": False}
                    break
            save_jira_config(instances)
            print(f"Jira '{selected_alias}' {new_status}.")
        return True
    return False


def load_mcp_tools() -> list[Tool]:
    mcp_config_path = Path.home() / ".config" / "gno6" / "mcp.json"

    if not mcp_config_path.exists():
        return []

    with open(mcp_config_path, "r") as f:
        mcp_urls = json.load(f).get("urls", [])

    if not mcp_urls:
        return []

    tools = []
    for entry in mcp_urls:
        if isinstance(entry, dict):
            url = entry.get("url", "")
            active = entry.get("active", True)
            if not active:
                continue
        else:
            url = entry
        try:
            mcp = Mcp(url)
            mcp.connect()
            tools.extend(mcp.get_tools_as(ToolType.OPENAI))
        except Exception as e:
            print(f"Failed to connect to MCP {url}: {e}")

    return tools


def main():
    (
        kubectl_exec_tool,
        helm_exec_tool,
        git_exec_tool,
        ask_question_tool,
        sleep_tool,
        task_is_solved_tool,
        list_files_tool,
        read_file_tool,
        write_file_tool,
        edit_file_tool,
        search_in_files,
        exec_script_tool,
    ) = init_tools()

    mcp_tools = load_mcp_tools()
    gitlab_tools = get_gitlab_tools()
    jira_tools = get_jira_tools()
    endpoint, api_key, model, endpoint_provider, log_level = get_config_from_env()
    main_agent = init_agent(endpoint, api_key, model, endpoint_provider, log_level)
    while True:
        init: bool = True

        print("Commands:\n*/history\n*/mcp\n*/gitlab\n*/jira")
        print("")
        user_query: str = questionary.autocomplete(
            "How may I help ?",
            choices=[
                "/new - Start a new conversation",
                "/history - Manage previous conversations",
                "/mcp - Manage MCP connections",
                "/gitlab - Manage GitLab connections",
                "/jira - Manage Jira connections",
            ],
            match_middle=False,
        ).ask()
        # user_query: str = questionary.text("How may I help with your cluster ?").ask()
        if user_query is None:
            return 0

        if manage_mcp_connections(user_query):
            mcp_tools = load_mcp_tools()
            continue

        if manage_gitlab_connections(user_query):
            gitlab_tools = get_gitlab_tools()
            continue

        if manage_jira_connections(user_query):
            jira_tools = get_jira_tools()
            continue

        cmd, agent_from_state = load_agent(user_query)
        if cmd is True:
            main_agent = agent_from_state
            continue

        Task(
            "We want to make sure that the given task has a clear final objective. How do you know that you have achieved/finished the task ? It has to be clear ! So, if you have a question, you can ask it using a tool. On the other hand, if the original task is clear and you understand what is expected from you then then we're good and you'll be able to start working next.",
            main_agent,
            tools=[ask_question_tool],
        )

        try:
            while True:
                uid: str = str(uuid.uuid4())
                prompt: str = (
                    "Do you need to use a tool"
                    if init is False
                    else f"You have received a task from the kubernetes cluster admin. <task>{user_query}</task>. Fulfill the admin's task using the tools at your disposition. Start with the planification phase then take action."
                )
                Task(
                    prompt,
                    main_agent,
                    tools=[
                        kubectl_exec_tool,
                        helm_exec_tool,
                        git_exec_tool,
                        sleep_tool,
                        ask_question_tool,
                        list_files_tool,
                        read_file_tool,
                        write_file_tool,
                        edit_file_tool,
                        search_in_files,
                    ]
                    + mcp_tools
                    + gitlab_tools
                    + jira_tools,
                    tags=["kubectl", uid],
                ).solve()
                init = False

                # Task("Do you have any questions to the cluster admin ? If you can continue working autonomously then cary on. Else use the tool to ask a question.", main_agent, tools=[ask_question_tool], tags=[uid]).solve()
                Task(
                    "In your opinion, is the initial task solved or should you keep working ?",
                    main_agent,
                    tools=[task_is_solved_tool],
                    tags=[uid],
                ).solve()

                # Task("", main_agent, tags=[uid])

                # print("Token count", main_agent.history.get_token_count())
                # if main_agent.history.get_token_count() > 10000:
                #  compact_history(main_agent)

        except TaskIsSolved:
            save_conversation(main_agent)


if __name__ == "__main__":
    main()
