from yacana import Agent, Task, Tool, Message, MessageRole, GroupSolve, EndChat, EndChatMode, LoggerManager, ToolError
from typing import Callable, List
import argparse

from qualification import qualify_request, get_request_qualification_ref
from team import Team
from tools import call_kubectl_cmd

print("Welcome to GnosisCTL, the smart kubectl CLI helper")




def add_minimal_k8s_help_to_history(main_agent: Agent) -> None:
    all_k8s_cmds: str = call_kubectl_cmd("kubectl --help")
    main_agent.history.add(Message(MessageRole.USER,
                              "To help you answer kubectl related questions I give you the kubectl --help output bellow:\n" + all_k8s_cmds))
    main_agent.history.add(Message(MessageRole.ASSISTANT,
                              "Okay thank you. I will use this piece of information to ground my answers and help me chose the correct kubectl action."))





############################################### Categories #########################################################

def knowledge_category(team: Team, user_query: str):
    print("The request was considered as general knowledge and no command will be proposed. I will "
          "still try to answer your question.")
    print("=> ", Task(f"{user_query}", team.main_agent).solve().content)


def complex_category(team: Team, user_query: str):
    simple_category(team, user_query)


def file_category(team: Team, user_query: str):
    raise NotImplemented("You requested file interactions like applying a Kubernetes manifest. This is not yet implemented. However we are working on it! ^^\nSorry for the inconvenience.")


def unrelated_category(team: Team, user_query: str):
    print("I acknowledge this information but won't output any kubectl commands. Still, I'll try to help you with your request.")
    llm_answer: str = Task(f"{user_query}", team.main_agent).solve().content
    return llm_answer


def arg_parsing() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process parameters to configure Gno6 runtime.")

    # Define optional named parameters with default values
    parser.add_argument('--model', type=str, default='llama3.1:8b', help='Specify the model name (default: llama3.1:8b)')
    parser.add_argument('--endpoint', type=str, default='http://127.0.0.1:11434', help='Specify the endpoint (default: http://127.0.0.1:11434)')
    parser.add_argument('--log-level', type=str, default=None, help='Specify the logging level. [None, DEBUG, INFO, WARNING WARN, ERROR] (default: None)')
    parser.add_argument('-n', '--namespace', type=str, default=None, help='Specify the K8s namespace inherent to the future generated command (default: None)')

    # Parse the arguments
    return parser.parse_args()





def main():

    args: argparse.Namespace = arg_parsing()
    team: Team = Team(args.model, args.endpoint, args.log_level, args.namespace)


    while True:
        print("How can I assist you with your kubectl commands ?")
        user_query: str = input("> ")
        print("Preparing...")

        request_type = qualify_request(team, user_query)

        if request_type == "simple" or request_type == "complex" or request_type == "file":
            add_minimal_k8s_help_to_history(team.main_agent)
        while True:
            ref: Callable = get_request_qualification_ref(request_type)
            # Calling function associated to the qualified request
            final_answer: str = ref(user_query)
            print('\n\033[96m' + final_answer + '\033[0m')

            success: bool = execute_command_in_place_of_user(team.main_agent, final_answer)
            if success is False:
                Task("Let's try to find a better kubectl command using the error output we got.", team.main_agent).solve()
            else:
                break
        team.reset()

main()
