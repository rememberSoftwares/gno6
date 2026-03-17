import json
from pathlib import Path
from typing import List, Optional
from yacana import ToolError

try:
    import gitlab
except ImportError:
    gitlab = None


_gitlab_clients: dict = {}


def _get_gitlab_client(alias: str):
    if gitlab is None:
        raise ToolError(
            "python-gitlab package is not installed. Install it with: pip install python-gitlab"
        )

    if alias not in _gitlab_clients:
        gitlab_config_path = Path.home() / ".config" / "gno6" / "gitlab.json"
        if not gitlab_config_path.exists():
            raise ToolError(
                f"No GitLab configuration found. Use /gitlab command to add a GitLab instance."
            )

        with open(gitlab_config_path, "r") as f:
            configs = json.load(f).get("instances", [])

        config = None
        for entry in configs:
            if isinstance(entry, dict) and entry.get("alias") == alias:
                config = entry
                break

        if config is None:
            raise ToolError(f"GitLab instance '{alias}' not found in configuration.")

        if not config.get("active", True):
            raise ToolError(f"GitLab instance '{alias}' is deactivated.")

        try:
            gl = gitlab.Gitlab(
                url=config["url"],
                private_token=config["token"],
                ssl_verify=config.get("ssl_verify", True),
            )
            _gitlab_clients[alias] = {
                "client": gl,
                "project_path": config["project_path"],
            }
        except Exception as e:
            raise ToolError(f"Failed to connect to GitLab instance '{alias}': {e}")

    return _gitlab_clients[alias]


def _get_project(alias: str):
    client_data = _get_gitlab_client(alias)
    gl = client_data["client"]
    project_path = client_data["project_path"]

    try:
        return gl.projects.get(project_path)
    except Exception as e:
        raise ToolError(f"Failed to get project '{project_path}': {e}")


def gitlab_list_aliases() -> List[str]:
    """
    List available GitLab instance aliases.
    """
    instances = load_gitlab_config()
    result = []
    for entry in instances:
        if isinstance(entry, dict) and entry.get("active", True):
            alias = entry.get("alias")
            if alias:
                result.append(alias)
    return result


def gitlab_get_issue(alias: str, issue_iid: int) -> dict:
    """
    Retrieve a GitLab issue by its IID.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_iid, int):
        raise ToolError(
            f"Tool argument `issue_iid` MUST be of type int. Got {type(issue_iid)}."
        )

    project = _get_project(alias)

    try:
        issue = project.issues.get(issue_iid)
        return {
            "iid": issue.iid,
            "title": issue.title,
            "description": issue.description,
            "state": issue.state,
            "labels": issue.labels,
        }
    except Exception as e:
        raise ToolError(f"Failed to get issue {issue_iid}: {e}")


def gitlab_list_issue_comments(alias: str, issue_iid: int) -> List[dict]:
    """
    List comments of a GitLab issue.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_iid, int):
        raise ToolError(
            f"Tool argument `issue_iid` MUST be of type int. Got {type(issue_iid)}."
        )

    project = _get_project(alias)

    try:
        issue = project.issues.get(issue_iid)
        comments = issue.notes.list(all=True)
        return [
            {
                "author": note.author["username"],
                "body": note.body,
                "created_at": note.created_at,
            }
            for note in comments
        ]
    except Exception as e:
        raise ToolError(f"Failed to list comments for issue {issue_iid}: {e}")


def gitlab_comment_issue(alias: str, issue_iid: int, body: str) -> str:
    """
    Add a comment to a GitLab issue.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_iid, int):
        raise ToolError(
            f"Tool argument `issue_iid` MUST be of type int. Got {type(issue_iid)}."
        )
    if not isinstance(body, str):
        raise ToolError(
            f"Tool argument `body` MUST be of type string. Got {type(body)}."
        )

    project = _get_project(alias)

    try:
        issue = project.issues.get(issue_iid)
        issue.notes.create({"body": body})
        return f"Comment added to issue {issue_iid}"
    except Exception as e:
        raise ToolError(f"Failed to comment on issue {issue_iid}: {e}")


def gitlab_close_issue(alias: str, issue_iid: int) -> str:
    """
    Close a GitLab issue.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_iid, int):
        raise ToolError(
            f"Tool argument `issue_iid` MUST be of type int. Got {type(issue_iid)}."
        )

    project = _get_project(alias)

    try:
        issue = project.issues.get(issue_iid)
        issue.state_event = "close"
        issue.save()
        return f"Issue {issue_iid} closed"
    except Exception as e:
        raise ToolError(f"Failed to close issue {issue_iid}: {e}")


def gitlab_create_issue(
    alias: str, title: str, description: str = "", labels: Optional[List[str]] = None
) -> dict:
    """
    Create a new GitLab issue.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(title, str):
        raise ToolError(
            f"Tool argument `title` MUST be of type string. Got {type(title)}."
        )
    if not isinstance(description, str):
        raise ToolError(
            f"Tool argument `description` MUST be of type string. Got {type(description)}."
        )

    if labels is None:
        labels = []
    elif not isinstance(labels, list):
        raise ToolError(
            f"Tool argument `labels` MUST be of type list. Got {type(labels)}."
        )

    project = _get_project(alias)

    try:
        issue_data = {
            "title": title,
            "description": description,
        }
        if labels:
            issue_data["labels"] = ",".join(labels)

        issue = project.issues.create(issue_data)
        return {
            "iid": issue.iid,
            "title": issue.title,
            "description": issue.description,
            "state": issue.state,
            "labels": issue.labels,
        }
    except Exception as e:
        raise ToolError(f"Failed to create issue: {e}")


def gitlab_add_label(alias: str, issue_iid: int, label: str) -> str:
    """
    Add a label to a GitLab issue.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_iid, int):
        raise ToolError(
            f"Tool argument `issue_iid` MUST be of type int. Got {type(issue_iid)}."
        )
    if not isinstance(label, str):
        raise ToolError(
            f"Tool argument `label` MUST be of type string. Got {type(label)}."
        )

    project = _get_project(alias)

    try:
        issue = project.issues.get(issue_iid)
        labels = list(issue.labels)
        if label not in labels:
            labels.append(label)
        issue.labels = labels
        issue.save()
        return f"Label '{label}' added to issue {issue_iid}"
    except Exception as e:
        raise ToolError(f"Failed to add label to issue {issue_iid}: {e}")


def gitlab_list_issues(alias: str, state: str = "opened") -> List[dict]:
    """
    List GitLab issues in the project.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(state, str):
        raise ToolError(
            f"Tool argument `state` MUST be of type string. Got {type(state)}."
        )

    project = _get_project(alias)

    try:
        issues = project.issues.list(state=state, all=True)
        return [
            {
                "iid": issue.iid,
                "title": issue.title,
                "state": issue.state,
                "labels": issue.labels,
            }
            for issue in issues
        ]
    except Exception as e:
        raise ToolError(f"Failed to list issues: {e}")


def load_gitlab_config() -> list:
    gitlab_config_path = Path.home() / ".config" / "gno6" / "gitlab.json"

    if not gitlab_config_path.exists():
        return []

    with open(gitlab_config_path, "r") as f:
        return json.load(f).get("instances", [])


def save_gitlab_config(instances: list):
    gitlab_config_path = Path.home() / ".config" / "gno6" / "gitlab.json"
    gitlab_config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(gitlab_config_path, "w") as f:
        json.dump({"instances": instances}, f, indent=2)


def get_gitlab_tools():
    from yacana import Tool, ToolType

    return [
        Tool(
            "gitlab_list_aliases",
            "List available GitLab instance aliases. Use this to discover which GitLab instances are configured.",
            gitlab_list_aliases,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "gitlab_get_issue",
            "Retrieve a GitLab issue by its IID.\n"
            ":param alias: GitLab instance alias (str)\n"
            ":param issue_iid: the issue IID (int)",
            gitlab_get_issue,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "gitlab_list_issue_comments",
            "List comments of a GitLab issue.\n"
            ":param alias: GitLab instance alias (str)\n"
            ":param issue_iid: the issue IID (int)",
            gitlab_list_issue_comments,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "gitlab_comment_issue",
            "Add a comment to a GitLab issue.\n"
            ":param alias: GitLab instance alias (str)\n"
            ":param issue_iid: the issue IID (int)\n"
            ":param body: comment text (str)",
            gitlab_comment_issue,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "gitlab_close_issue",
            "Close a GitLab issue.\n"
            ":param alias: GitLab instance alias (str)\n"
            ":param issue_iid: the issue IID (int)",
            gitlab_close_issue,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "gitlab_create_issue",
            "Create a new GitLab issue.\n"
            ":param alias: GitLab instance alias (str)\n"
            ":param title: issue title (str)\n"
            ":param description: issue description (str, optional)\n"
            ":param labels: list of label names (list of str, optional)",
            gitlab_create_issue,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "gitlab_add_label",
            "Add a label to a GitLab issue.\n"
            ":param alias: GitLab instance alias (str)\n"
            ":param issue_iid: the issue IID (int)\n"
            ":param label: label name (str)",
            gitlab_add_label,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "gitlab_list_issues",
            "List GitLab issues in the project.\n"
            ":param alias: GitLab instance alias (str)\n"
            ":param state: 'opened' or 'closed' (str)",
            gitlab_list_issues,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
    ]
