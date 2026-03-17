import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from yacana import ToolError

try:
    import requests
except ImportError:
    requests = None


_jira_clients: dict = {}


class JiraClient:
    def __init__(
        self, base_url: str, email: str, api_token: str, verify_ssl: bool = True
    ):
        self.base_url = base_url.rstrip("/")
        self.auth = (email, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.verify_ssl = verify_ssl

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = requests.request(
            method,
            url,
            auth=self.auth,
            headers=self.headers,
            verify=self.verify_ssl,
            **kwargs,
        )

        if not response.ok:
            raise Exception(f"Jira API error {response.status_code}: {response.text}")

        if response.text:
            return response.json()
        return {}

    def search_issues(
        self, jql: str, max_results: int = 10, fields: str = "summary,key"
    ):
        data = self._request(
            "GET",
            "/rest/api/3/search/jql",
            params={
                "jql": jql,
                "maxResults": max_results,
                "fields": fields,
            },
        )
        return data.get("issues", [])

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        return self._request("GET", f"/rest/api/3/issue/{issue_key}")

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
    ) -> Dict[str, Any]:
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": issue_type},
            }
        }

        return self._request("POST", "/rest/api/3/issue", json=payload)

    def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }

        return self._request(
            "POST",
            f"/rest/api/3/issue/{issue_key}/comment",
            json=payload,
        )

    def get_transitions(self, issue_key: str) -> List[Dict[str, Any]]:
        data = self._request(
            "GET",
            f"/rest/api/3/issue/{issue_key}/transitions",
        )
        return data.get("transitions", [])

    def transition_issue(self, issue_key: str, transition_id: str) -> Dict[str, Any]:
        payload = {
            "transition": {
                "id": transition_id,
            }
        }

        return self._request(
            "POST",
            f"/rest/api/3/issue/{issue_key}/transitions",
            json=payload,
        )

    def get_projects(self):
        return self._request("GET", "/rest/api/3/project")

    def get_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        data = self._request(
            "GET",
            f"/rest/api/3/issue/{issue_key}/comment",
        )
        return data.get("comments", [])


def _get_jira_client(alias: str) -> JiraClient:
    if requests is None:
        raise ToolError(
            "requests package is not installed. Install it with: pip install requests"
        )

    if alias not in _jira_clients:
        jira_config_path = Path.home() / ".config" / "gno6" / "jira.json"
        if not jira_config_path.exists():
            raise ToolError(
                f"No Jira configuration found. Use /jira command to add a Jira instance."
            )

        with open(jira_config_path, "r") as f:
            configs = json.load(f).get("instances", [])

        config = None
        for entry in configs:
            if isinstance(entry, dict) and entry.get("alias") == alias:
                config = entry
                break

        if config is None:
            raise ToolError(f"Jira instance '{alias}' not found in configuration.")

        if not config.get("active", True):
            raise ToolError(f"Jira instance '{alias}' is deactivated.")

        try:
            client = JiraClient(
                base_url=config["url"],
                email=config["email"],
                api_token=config["api_token"],
                verify_ssl=config.get("verify_ssl", True),
            )
            _jira_clients[alias] = client
        except Exception as e:
            raise ToolError(f"Failed to connect to Jira instance '{alias}': {e}")

    return _jira_clients[alias]


def jira_list_aliases() -> List[str]:
    """
    List available Jira instance aliases.
    """
    instances = load_jira_config()
    result = []
    for entry in instances:
        if isinstance(entry, dict) and entry.get("active", True):
            alias = entry.get("alias")
            if alias:
                result.append(alias)
    return result


def jira_get_issue(alias: str, issue_key: str) -> dict:
    """
    Retrieve a Jira issue by its key.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_key, str):
        raise ToolError(
            f"Tool argument `issue_key` MUST be of type string. Got {type(issue_key)}."
        )

    client = _get_jira_client(alias)

    try:
        issue = client.get_issue(issue_key)
        fields = issue.get("fields", {})

        linked_issues = []
        for link in fields.get("issuelinks", []):
            link_type = link.get("type", {})
            link_type_name = link_type.get("name", "")

            if "outwardIssue" in link:
                outward = link["outwardIssue"]
                outward_fields = outward.get("fields", {})
                linked_issues.append(
                    {
                        "key": outward.get("key"),
                        "summary": outward_fields.get("summary"),
                        "status": outward_fields.get("status", {}).get("name"),
                        "type": link_type.get("outward", link_type_name),
                    }
                )

            if "inwardIssue" in link:
                inward = link["inwardIssue"]
                inward_fields = inward.get("fields", {})
                linked_issues.append(
                    {
                        "key": inward.get("key"),
                        "summary": inward_fields.get("summary"),
                        "status": inward_fields.get("status", {}).get("name"),
                        "type": link_type.get("inward", link_type_name),
                    }
                )

        return {
            "key": issue.get("key"),
            "summary": fields.get("summary"),
            "description": fields.get("description"),
            "status": fields.get("status", {}).get("name"),
            "issuetype": fields.get("issuetype", {}).get("name"),
            "linked_issues": linked_issues,
        }
    except Exception as e:
        raise ToolError(f"Failed to get issue {issue_key}: {e}")


def jira_search_issues(alias: str, jql: str, max_results: int = 10) -> List[dict]:
    """
    Search Jira issues using JQL.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(jql, str):
        raise ToolError(f"Tool argument `jql` MUST be of type string. Got {type(jql)}.")
    if not isinstance(max_results, int):
        raise ToolError(
            f"Tool argument `max_results` MUST be of type int. Got {type(max_results)}."
        )

    client = _get_jira_client(alias)

    try:
        issues = client.search_issues(jql, max_results=max_results)
        return [
            {
                "key": issue.get("key"),
                "summary": issue.get("fields", {}).get("summary"),
            }
            for issue in issues
        ]
    except Exception as e:
        raise ToolError(f"Failed to search issues: {e}")


def jira_create_issue(
    alias: str,
    project_key: str,
    summary: str,
    description: str = "",
    issue_type: str = "Task",
) -> dict:
    """
    Create a new Jira issue.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(project_key, str):
        raise ToolError(
            f"Tool argument `project_key` MUST be of type string. Got {type(project_key)}."
        )
    if not isinstance(summary, str):
        raise ToolError(
            f"Tool argument `summary` MUST be of type string. Got {type(summary)}."
        )
    if not isinstance(description, str):
        raise ToolError(
            f"Tool argument `description` MUST be of type string. Got {type(description)}."
        )
    if not isinstance(issue_type, str):
        raise ToolError(
            f"Tool argument `issue_type` MUST be of type string. Got {type(issue_type)}."
        )

    client = _get_jira_client(alias)

    try:
        issue = client.create_issue(project_key, summary, description, issue_type)
        return {
            "key": issue.get("key"),
            "id": issue.get("id"),
        }
    except Exception as e:
        raise ToolError(f"Failed to create issue: {e}")


def jira_add_comment(alias: str, issue_key: str, comment: str) -> str:
    """
    Add a comment to a Jira issue.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_key, str):
        raise ToolError(
            f"Tool argument `issue_key` MUST be of type string. Got {type(issue_key)}."
        )
    if not isinstance(comment, str):
        raise ToolError(
            f"Tool argument `comment` MUST be of type string. Got {type(comment)}."
        )

    client = _get_jira_client(alias)

    try:
        client.add_comment(issue_key, comment)
        return f"Comment added to issue {issue_key}"
    except Exception as e:
        raise ToolError(f"Failed to add comment to issue {issue_key}: {e}")


def jira_get_comments(alias: str, issue_key: str) -> List[dict]:
    """
    List comments of a Jira issue.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_key, str):
        raise ToolError(
            f"Tool argument `issue_key` MUST be of type string. Got {type(issue_key)}."
        )

    client = _get_jira_client(alias)

    try:
        comments = client.get_comments(issue_key)
        result = []
        for c in comments:
            body = c.get("body", {})
            text = ""
            if isinstance(body, dict):
                content = body.get("content", [])
                for paragraph in content:
                    if paragraph.get("type") == "paragraph":
                        for text_item in paragraph.get("content", []):
                            if text_item.get("type") == "text":
                                text += text_item.get("text", "")
            result.append(
                {
                    "author": c.get("author", {}).get("displayName", ""),
                    "body": text,
                    "created": c.get("created", ""),
                }
            )
        return result
    except Exception as e:
        raise ToolError(f"Failed to get comments for issue {issue_key}: {e}")


def jira_get_transitions(alias: str, issue_key: str) -> List[dict]:
    """
    Get available transitions for a Jira issue.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_key, str):
        raise ToolError(
            f"Tool argument `issue_key` MUST be of type string. Got {type(issue_key)}."
        )

    client = _get_jira_client(alias)

    try:
        transitions = client.get_transitions(issue_key)
        return [
            {
                "id": t.get("id"),
                "name": t.get("name"),
            }
            for t in transitions
        ]
    except Exception as e:
        raise ToolError(f"Failed to get transitions for issue {issue_key}: {e}")


def jira_transition_issue(alias: str, issue_key: str, transition_id: str) -> str:
    """
    Transition a Jira issue to a new status.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )
    if not isinstance(issue_key, str):
        raise ToolError(
            f"Tool argument `issue_key` MUST be of type string. Got {type(issue_key)}."
        )
    if not isinstance(transition_id, str):
        raise ToolError(
            f"Tool argument `transition_id` MUST be of type string. Got {type(transition_id)}."
        )

    client = _get_jira_client(alias)

    try:
        client.transition_issue(issue_key, transition_id)
        return f"Issue {issue_key} transitioned"
    except Exception as e:
        raise ToolError(f"Failed to transition issue {issue_key}: {e}")


def jira_get_projects(alias: str) -> List[dict]:
    """
    List Jira projects.
    """
    if not isinstance(alias, str):
        raise ToolError(
            f"Tool argument `alias` MUST be of type string. Got {type(alias)}."
        )

    client = _get_jira_client(alias)

    try:
        projects = client.get_projects()
        return [
            {
                "key": p.get("key"),
                "name": p.get("name"),
            }
            for p in projects
        ]
    except Exception as e:
        raise ToolError(f"Failed to list projects: {e}")


def load_jira_config() -> list:
    jira_config_path = Path.home() / ".config" / "gno6" / "jira.json"

    if not jira_config_path.exists():
        return []

    with open(jira_config_path, "r") as f:
        return json.load(f).get("instances", [])


def save_jira_config(instances: list):
    jira_config_path = Path.home() / ".config" / "gno6" / "jira.json"
    jira_config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(jira_config_path, "w") as f:
        json.dump({"instances": instances}, f, indent=2)


def get_jira_tools():
    from yacana import Tool, ToolType

    return [
        Tool(
            "jira_list_aliases",
            "List available Jira instance aliases. Use this to discover which Jira instances are configured.",
            jira_list_aliases,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "jira_get_issue",
            "Retrieve a Jira issue by its key.\n"
            ":param alias: Jira instance alias (str)\n"
            ":param issue_key: the issue key (str, e.g. PROJ-123)",
            jira_get_issue,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "jira_search_issues",
            "Search Jira issues using JQL (Jira Query Language).\n"
            ":param alias: Jira instance alias (str)\n"
            ":param jql: JQL query string (str)\n"
            ":param max_results: maximum number of results (int, default 10)",
            jira_search_issues,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "jira_create_issue",
            "Create a new Jira issue.\n"
            ":param alias: Jira instance alias (str)\n"
            ":param project_key: project key (str)\n"
            ":param summary: issue summary/title (str)\n"
            ":param description: issue description (str, optional)\n"
            ":param issue_type: issue type name (str, default 'Task')",
            jira_create_issue,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "jira_add_comment",
            "Add a comment to a Jira issue.\n"
            ":param alias: Jira instance alias (str)\n"
            ":param issue_key: the issue key (str)\n"
            ":param comment: comment text (str)",
            jira_add_comment,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "jira_get_comments",
            "List comments of a Jira issue.\n"
            ":param alias: Jira instance alias (str)\n"
            ":param issue_key: the issue key (str)",
            jira_get_comments,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "jira_get_transitions",
            "Get available transitions for a Jira issue.\n"
            ":param alias: Jira instance alias (str)\n"
            ":param issue_key: the issue key (str)",
            jira_get_transitions,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "jira_transition_issue",
            "Transition a Jira issue to a new status.\n"
            ":param alias: Jira instance alias (str)\n"
            ":param issue_key: the issue key (str)\n"
            ":param transition_id: transition ID (str)",
            jira_transition_issue,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
        Tool(
            "jira_get_projects",
            "List Jira projects.\n:param alias: Jira instance alias (str)",
            jira_get_projects,
            max_custom_error=70,
            max_call_error=70,
            optional=True,
            tool_type=ToolType.OPENAI,
        ),
    ]
