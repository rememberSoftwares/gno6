import json
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from questionary import Choice
except ImportError:
    Choice = None

JIRA_TOOL_NAMES = [
    "jira_list_aliases",
    "jira_get_issue",
    "jira_search_issues",
    "jira_create_issue",
    "jira_add_comment",
    "jira_get_comments",
    "jira_get_transitions",
    "jira_transition_issue",
    "jira_get_projects",
]

GITLAB_TOOL_NAMES = [
    "gitlab_list_aliases",
    "gitlab_get_issue",
    "gitlab_list_issue_comments",
    "gitlab_comment_issue",
    "gitlab_close_issue",
    "gitlab_create_issue",
    "gitlab_add_label",
    "gitlab_list_issues",
    "gitlab_get_mr",
    "gitlab_list_mrs",
    "gitlab_create_mr",
    "gitlab_close_mr",
    "gitlab_comment_mr",
    "gitlab_list_mr_comments",
]

BASE_TOOL_NAMES = [
    "kubectl_exec",
    "helm_exec",
    "git_exec",
    "human_in_the_loop",
    "sleep",
    "task_is_solved",
    "list_files",
    "read_file",
    "write_file",
    "edit_file",
    "search_in_files",
    "exec_script",
]

DEFAULT_TOOLS = [
    {"name": "kubectl_exec", "display": "Kubectl", "active": True},
    {"name": "helm_exec", "display": "Helm", "active": True},
    {"name": "git_exec", "display": "Git", "active": True},
    {"name": "human_in_the_loop", "display": "Ask Question", "active": True},
    {"name": "sleep", "display": "Sleep", "active": True},
    {"name": "task_is_solved", "display": "Task Complete", "active": True},
    {"name": "list_files", "display": "List Files", "active": True},
    {"name": "read_file", "display": "Read File", "active": True},
    {"name": "write_file", "display": "Write File", "active": True},
    {"name": "edit_file", "display": "Edit File", "active": True},
    {"name": "search_in_files", "display": "Search Files", "active": True},
    {"name": "exec_script", "display": "Run Script", "active": True},
    {
        "name": "gitlab_list_aliases",
        "display": "GitLab: List Instances",
        "active": True,
    },
    {"name": "gitlab_get_issue", "display": "GitLab: Get Issue", "active": True},
    {
        "name": "gitlab_list_issue_comments",
        "display": "GitLab: Get Issue Comments",
        "active": True,
    },
    {
        "name": "gitlab_comment_issue",
        "display": "GitLab: Comment Issue",
        "active": True,
    },
    {"name": "gitlab_close_issue", "display": "GitLab: Close Issue", "active": True},
    {"name": "gitlab_create_issue", "display": "GitLab: Create Issue", "active": True},
    {"name": "gitlab_add_label", "display": "GitLab: Add Label", "active": True},
    {"name": "gitlab_list_issues", "display": "GitLab: List Issues", "active": True},
    {"name": "gitlab_get_mr", "display": "GitLab: Get Merge Request", "active": True},
    {
        "name": "gitlab_list_mrs",
        "display": "GitLab: List Merge Requests",
        "active": True,
    },
    {
        "name": "gitlab_create_mr",
        "display": "GitLab: Create Merge Request",
        "active": True,
    },
    {
        "name": "gitlab_close_mr",
        "display": "GitLab: Close Merge Request",
        "active": True,
    },
    {
        "name": "gitlab_comment_mr",
        "display": "GitLab: Comment Merge Request",
        "active": True,
    },
    {
        "name": "gitlab_list_mr_comments",
        "display": "GitLab: Get MR Comments",
        "active": True,
    },
    {"name": "jira_list_aliases", "display": "Jira: List Instances", "active": True},
    {"name": "jira_get_issue", "display": "Jira: Get Issue", "active": True},
    {"name": "jira_search_issues", "display": "Jira: Search Issues", "active": True},
    {"name": "jira_create_issue", "display": "Jira: Create Issue", "active": True},
    {"name": "jira_add_comment", "display": "Jira: Add Comment", "active": True},
    {"name": "jira_get_comments", "display": "Jira: Get Comments", "active": True},
    {
        "name": "jira_get_transitions",
        "display": "Jira: Get Transitions",
        "active": True,
    },
    {
        "name": "jira_transition_issue",
        "display": "Jira: Transition Issue",
        "active": True,
    },
    {"name": "jira_get_projects", "display": "Jira: List Projects", "active": True},
]


def load_json_config(config_path: Path, key: str) -> list:
    if not config_path.exists():
        return []
    with open(config_path, "r") as f:
        return json.load(f).get(key, [])


def save_json_config(config_path: Path, key: str, data: list):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({key: data}, f, indent=2)


def get_config_dir() -> Path:
    return Path.home() / ".config" / "gno6"


def load_tools_config() -> list:
    return load_json_config(get_config_dir() / "tools.json", "tools")


def save_tools_config(tools: list):
    save_json_config(get_config_dir() / "tools.json", "tools", tools)


def load_agents_config() -> list:
    return load_json_config(get_config_dir() / "agents.json", "agents")


def save_agents_config(agents: list):
    save_json_config(get_config_dir() / "agents.json", "agents", agents)


def load_jira_config() -> list:
    return load_json_config(get_config_dir() / "jira.json", "instances")


def load_gitlab_config() -> list:
    return load_json_config(get_config_dir() / "gitlab.json", "instances")


def merge_tools_config(existing: list) -> list:
    existing_names = set()
    for entry in existing:
        if isinstance(entry, dict):
            existing_names.add(entry.get("name"))
        else:
            existing_names.add(entry)
    merged = list(existing)
    for tool in DEFAULT_TOOLS:
        if tool["name"] not in existing_names:
            merged.append(tool)
    return merged


def build_tool_choices(
    tools_config: list,
    available_tool_names: list,
) -> Tuple[List[str], dict]:
    tool_choices = []
    choice_to_name = {}
    for entry in tools_config:
        if isinstance(entry, dict):
            name_t = entry.get("name", "")
            if name_t in available_tool_names:
                display = entry.get("display", name_t)
                choice_str = f"{display} ({name_t})"
                tool_choices.append(choice_str)
                choice_to_name[choice_str] = name_t
    return tool_choices, choice_to_name


def compute_default_disabled(
    tool_choices: List[str],
    choice_to_name: dict,
    tool_names: Optional[List[str]],
    old_available_tool_names: List[str],
) -> List[str]:
    if not tool_names:
        return []

    active_set = set(tool_names)
    old_available_set = set(old_available_tool_names)
    default_disabled = []

    for choice_str in tool_choices:
        name = choice_to_name.get(choice_str)
        if name and name in old_available_set and name not in active_set:
            default_disabled.append(choice_str)

    return default_disabled


def filter_valid_defaults(defaults: List[str], choices: List[str]) -> List[str]:
    choices_set = set(choices)
    return [d for d in defaults if d in choices_set]


def configure_agent(
    jira_aliases: Optional[List[str]] = None,
    gitlab_aliases: Optional[List[str]] = None,
    tool_names: Optional[List[str]] = None,
    questionary_module=None,
) -> Tuple[Optional[List[str]], Optional[List[str]], Optional[List[str]]]:
    """
    Configure an agent with Jira, GitLab instances and tools.

    Returns (jira_aliases, gitlab_aliases, tool_names) or (None, None, None) on cancel.
    """
    if questionary_module is None:
        import questionary
    else:
        questionary = questionary_module

    jira_instances = load_jira_config()
    jira_choices = []
    for inst in jira_instances:
        if isinstance(inst, dict) and inst.get("active", True):
            alias = inst.get("alias", "")
            if alias:
                jira_choices.append(alias)

    if jira_choices:
        jira_choices_set = set(jira_choices)
        valid_jira_defaults = set(
            a for a in (jira_aliases or []) if a in jira_choices_set
        )
        if Choice is not None:
            choices = [
                Choice(alias, checked=alias in valid_jira_defaults)
                for alias in jira_choices
            ]
        else:
            choices = jira_choices
        try:
            selected_jira = questionary.checkbox(
                "Select Jira instances (space to select, enter to confirm):",
                choices=choices,
            ).ask()
        except KeyboardInterrupt:
            return None, None, None
    else:
        selected_jira = []
        if jira_aliases is None:
            print("No Jira instances configured.")

    new_jira_aliases = selected_jira if selected_jira else []

    gitlab_instances = load_gitlab_config()
    gitlab_choices = []
    for inst in gitlab_instances:
        if isinstance(inst, dict) and inst.get("active", True):
            alias = inst.get("alias", "")
            if alias:
                gitlab_choices.append(alias)

    if gitlab_choices:
        gitlab_choices_set = set(gitlab_choices)
        valid_gitlab_defaults = set(
            a for a in (gitlab_aliases or []) if a in gitlab_choices_set
        )
        if Choice is not None:
            choices = [
                Choice(alias, checked=alias in valid_gitlab_defaults)
                for alias in gitlab_choices
            ]
        else:
            choices = gitlab_choices
        try:
            selected_gitlab = questionary.checkbox(
                "Select GitLab instances (space to select, enter to confirm):",
                choices=choices,
            ).ask()
        except KeyboardInterrupt:
            return None, None, None
    else:
        selected_gitlab = []
        if gitlab_aliases is None:
            print("No GitLab instances configured.")

    new_gitlab_aliases = selected_gitlab if selected_gitlab else []

    tools_config = load_tools_config()
    available_tool_names = list(BASE_TOOL_NAMES)

    if new_jira_aliases:
        available_tool_names.extend(JIRA_TOOL_NAMES)
    if new_gitlab_aliases:
        available_tool_names.extend(GITLAB_TOOL_NAMES)

    old_available_tool_names = list(BASE_TOOL_NAMES)
    if jira_aliases:
        old_available_tool_names.extend(JIRA_TOOL_NAMES)
    if gitlab_aliases:
        old_available_tool_names.extend(GITLAB_TOOL_NAMES)

    tool_choices, choice_to_name = build_tool_choices(
        tools_config, available_tool_names
    )

    default_disabled = compute_default_disabled(
        tool_choices, choice_to_name, tool_names, old_available_tool_names
    )

    if tool_choices:
        print("All tools are enabled by default. Select tools to DISABLE:")
        safe_defaults = set(filter_valid_defaults(default_disabled, tool_choices))
        if Choice is not None:
            choices = [
                Choice(choice, checked=choice in safe_defaults)
                for choice in tool_choices
            ]
        else:
            choices = tool_choices
        try:
            selected_disabled = questionary.checkbox(
                "Select tools to disable (space to select, enter to confirm):",
                choices=choices,
            ).ask()
        except KeyboardInterrupt:
            return None, None, None
    else:
        selected_disabled = []

    disabled_names = set()
    if selected_disabled:
        for t in selected_disabled:
            name = choice_to_name.get(t)
            if name:
                disabled_names.add(name)

    new_tool_names = [t for t in available_tool_names if t not in disabled_names]

    return new_jira_aliases, new_gitlab_aliases, new_tool_names
