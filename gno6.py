from yacana import Task
import argparse

from CategoryFactory import CategoryFactory
from category import Category
from execute import execute_command_in_place_of_user
from k8s_utils import add_minimal_k8s_help_to_history
from qualification import qualify_request
from team import Team


print("Welcome to GnosisCTL, the smart kubectl CLI helper\n")


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

        category_type = qualify_request(team, user_query)

        if category_type == "simple" or category_type == "complex" or category_type == "file":
            add_minimal_k8s_help_to_history(team.main_agent)
        while True:
            category: Category = CategoryFactory.get_category(category_type, user_query, team)
            # Calling function associated to the qualified request
            final_command: str = category.start_workflow()

            print('\n\033[96m' + final_command + '\033[0m')

            success: bool = execute_command_in_place_of_user(team.main_agent, final_command)
            if success is False:
                Task("Let's try to find a better kubectl command using the error output we got.", team.main_agent).solve()
            else:
                break
        team.reset()


main()
