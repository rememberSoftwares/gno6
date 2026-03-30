import os
import questionary
from yacana import ToolError, OllamaAgent, OpenAiAgent, GenericAgent, LoggerManager
from . import config

ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"
ANSI_BOLD = "\x1b[1m"

MAIN_SYSTEM_PROMPT = """You are a helpful AI DEVOPS assistant expert on kubernetes. Your job is to fulfill a DEVOPS related task given by the Kubernetes cluster admin. To help you fulfill the task you have access to a list of tools letting you interact with k8s cluters, Gitlab or Jira. Use them wisely. When debbuging, always follow this approch:

# PLANIFICATION PHASE
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


def get_config_from_env():
    """
    Validating credentials are present
    """
    inter = False
    try:
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
    except KeyboardInterrupt:
        print("\nGoodbye!")
        os._exit(0)

    if inter is True:
        print(f"""Set these ENV variables so you don't have to do this again:
export GNO6_ENDPOINT={endpoint}
export GNO6_API_KEY={api_key}
export GNO6_MODEL={model}
export GNO6_PROVIDER={provider}
export GNO6_LOG_LEVEL={log_level}
""")
    return (endpoint, api_key, model, provider, log_level)


def init_agent(
    endpoint: str,
    api_key: str,
    model: str,
    type: str,
    logging_level=None,
    system_prompt: str = None,
) -> GenericAgent:
    if system_prompt is None:
        system_prompt = MAIN_SYSTEM_PROMPT

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


def confirm_exec(question: str):
    while True:
        confirmed: bool = questionary.confirm(question).ask()
        if confirmed:
            break
        elif not confirmed:
            reason: str = questionary.text(
                "Reason to give the LLM why you said no."
            ).ask()
            raise ToolError(
                f"Tool was denied by the cluster admin with the following reason : {reason}"
            )
