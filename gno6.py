from yacana import Agent, Task, Tool, Message, MessageRole, GroupSolve, EndChat, EndChatMode, LoggerManager, ToolError

import subprocess
from typing import Callable, List
import re
import argparse

from qualification import qualify_request
from team import Team

print("Welcome to GnosisCTL, the smart kubectl CLI helper")

main_agent: Agent = None
assessment_agent: Agent = None
logic_agent: Agent = None
k8s_help_agent: Agent = None

def call_kubectl_cmd(cmd: str):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, timeout=20,
                                       universal_newlines=True)
    except subprocess.CalledProcessError as e:
        raise ToolError(repr(
            e.output) + '\nRemember that you must call this tool with a kubectl action and a kubectl resource. For instance: {"action_verb": "get", "resource": "pod"}')


def get_cmd_help(action_verb: str, resource_type: str) -> str:
    #print(f"Tool is called with {action_verb} and {resource_type}")

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


def explain_missing_kubectl() -> str:
    GroupSolve(
        [Task("It seems like the command you outputted doesn't start with 'kubectl'. Is this normal ?", main_agent),
         Task(
             "A kubectl command was created to match the query of a user. However the command did not start with 'kubectl' which seems strange. Investigate why. You task is done when you are sure that the command starts with 'kubectl'.",
             logic_agent, llm_stops_by_itself=True)],
        EndChat(EndChatMode.END_CHAT_AFTER_FIRST_COMPLETION, max_iterations=2)).solve()
    final_cmd: str = Task(
        "After deliberation what is the final kubectl command ? Only output the command and NOTHING ELSE",
        main_agent).solve().content
    return final_cmd


def add_minimal_k8s_help_to_history(agent: Agent) -> None:
    all_k8s_cmds: str = call_kubectl_cmd("kubectl --help")
    agent.history.add(Message(MessageRole.USER,
                              "To help you answer kubectl related questions I give you the kubectl --help output bellow:\n" + all_k8s_cmds))
    agent.history.add(Message(MessageRole.ASSISTANT,
                              "Okay thank you. I will use this piece of information to ground my answers and help me chose the correct kubectl action."))


def final_command_output(k_nb_occurrences: int) -> str:
    command = Task(
        f"Now that you have brainstormed and validated the command{'s' if k_nb_occurrences else ''}. Please output the final version. Only output the command{'s' if k_nb_occurrences else ''} and nothing else.",
        main_agent).solve().content
    if not command.startswith("kubectl"):
        command = explain_missing_kubectl()
    #print(f"=> {command}")
    return command


############################################### Categories #########################################################

def knowledge_category(user_query: str):
    print("The request was considered as general knowledge and no command will be proposed. I will "
          "still try to answer your question.")
    print("=> ", Task(f"{user_query}", main_agent).solve().content)





def complex_category(user_query: str):
    simple_category(user_query)


def file_category(user_query: str):
    raise NotImplemented("You requested file interactions like applying a Kubernetes manifest. This is not yet implemented. However we are working on it! ^^\nSorry for the inconvenience.")


def unrelated_category(user_query: str):
    print("I acknowledge this information but won't output any kubectl commands. Still, I'll try to help you with your request.")
    llm_answer: str = Task(f"{user_query}", main_agent).solve().content
    return llm_answer





def init_agents(model: str, endpoint: str, logging_level, namespace: str | None) -> Team:
    global main_agent
    global assessment_agent
    global logic_agent
    global k8s_help_agent

    main_agent = Agent("main_agent", model,
                       system_prompt="You are a helpful AI assistant expert on kubectl commands and kubernetes clusters. Your end goal is to generate a valid kubectl command based on the user query.", endpoint=endpoint)
    assessment_agent = Agent("Assessment_agent", model,
                             system_prompt="You are an AI assistant with the goal to qualify user requests into predefined categories.", endpoint=endpoint)
    logic_agent = Agent("Logic_agent", model,
                        system_prompt="You are an AI assistant that reflects on other's problematic by asking question and ensuring that the response given in return is logic.", endpoint=endpoint)
    k8s_help_agent = Agent("K8s_validator", model,
                           system_prompt="You are an AI assistant that can access kubectl command line help. You make sure that kubectl commands are valid and help refacto them if needed.", endpoint=endpoint)
    LoggerManager.set_log_level(None if logging_level == "None" else logging_level)

    if namespace is not None:
        main_agent.history.add(Message(MessageRole.USER, f"Targeted Kubernetes namespace is {namespace}"))
        main_agent.history.add(Message(MessageRole.ASSISTANT, f"Okay! Now on, all Kubernetes commands should set this argument: '-n {namespace}'"))
    return Team(main_agent, assessment_agent, logic_agent, k8s_help_agent)

def reset_agents(agents: List[Agent]) -> None:
    for agent in agents:  # if we keep that we loose the knowledge history. So maybe the function that treats this part should be added to the main_agent after the clean
        agent.history.clean()


def arg_parsing() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process parameters to configure Gno6 runtime.")

    # Define optional named parameters with default values
    parser.add_argument('--model', type=str, default='llama3.1:8b', help='Specify the model name (default: llama3.1:8b)')
    parser.add_argument('--endpoint', type=str, default='http://127.0.0.1:11434', help='Specify the endpoint (default: http://127.0.0.1:11434)')
    parser.add_argument('--log-level', type=str, default=None, help='Specify the logging level. [None, DEBUG, INFO, WARNING WARN, ERROR] (default: None)')
    parser.add_argument('-n', '--namespace', type=str, default=None, help='Specify the K8s namespace inherent to the future generated command (default: None)')

    # Parse the arguments
    return parser.parse_args()


def exec_kubectl_cmd(kubectl_cmd: str) -> str:
    try:
        # result = subprocess.run(final_cmd, shell=True, check=True, text=True, capture_output=True, stderr=subprocess.STDOUT)
        result = subprocess.check_output(kubectl_cmd, stderr=subprocess.STDOUT, shell=True, timeout=20, universal_newlines=True)
        if not any(char.isalpha() or char.isdigit() for char in result):
            raise RuntimeError(
                f"Error: kubectl command returned an empty string. {'If the jsonpath expression is wrong it may return an empty result. The problem might come from there.' if 'jsonpath' in kubectl_cmd else ''}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(repr(e.output))
    return result


def execute_command_in_place_of_user(k8s_cmd: str) -> bool:
    """

    :param k8s_cmd:
    :return: bool : Success or failure
    """
    print("\nShould I execute the command for you?")
    should_execute: str = input("> ")
    router: str = Task("The user was asked a 'yes'/'no' question. Determine what was his choice and ONLY output 'yes' if it was affirmative else ONLY output 'no'.", main_agent, forget=True).solve().content
    if "yes" in router.lower():
        try:
            cmd_output = exec_kubectl_cmd(k8s_cmd)
        except RuntimeError as e:
            cmd_output = str(e)
            print("ERROR occurred :-(")
        print('\n\033[96m' + cmd_output + '\033[0m')
        Task(f"Your task is to asses the output of execution of this kubectl command: `{k8s_cmd}`\nYou must determine if the execution is a success or a failure. The output is the following: {cmd_output}", main_agent).solve()
        router: str = Task("Was the command a complete success ? Answer ONLY by 'yes' or by 'no'", main_agent, forget=True).solve().content
        if "yes" in router.lower():
            print("\nCommand execution was a success.")
        else:
            print("Command execution was a failure. Let's analyse what when wrong!")
            error_summary = Task("Write a very brief summary of what went wrong in your opinion.", main_agent).solve().content
            print(error_summary)
            return False
    return True


def main():

    args: argparse.Namespace = arg_parsing()
    team: Team = init_agents(args.model, args.endpoint, args.log_level, args.namespace)
    agents: List[Agent] = [main_agent, assessment_agent, logic_agent, k8s_help_agent]
    # Removing 'ref' field from the query_qualification array
    query_qualification_stripped = [{k: v for k, v in item.items() if k != 'ref'} for item in query_qualification]

    while True:
        print("How can I assist you with your kubectl commands ?")
        user_query: str = input("> ")
        print("Preparing...")

        uuid = qualify_request()


        if uid == "simple" or uid == "complex" or uid == "file":
            add_minimal_k8s_help_to_history(main_agent)
        while True:
            ref: Callable = next((qual["ref"] for qual in query_qualification if qual["uid"] == uid), None)
            final_answer: str = ref(user_query)
            print('\n\033[96m' + final_answer + '\033[0m')

            success: bool = execute_command_in_place_of_user(final_answer)
            if success is False:
                Task("Let's try to find a better kubectl command using the error output we got.", main_agent).solve()
            else:
                break

        reset_agents(agents)

main()
