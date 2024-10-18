import json

from yacana import Task, Message, MessageRole

from category import Category
from common_utils import final_command_output
from k8s_utils import explain_missing_kubectl
from team import Team


class SimpleCategory(Category):

    def __init__(self, user_query: str, team: Team):
        self.user_query = user_query
        self.team: Team = team

    def start_workflow(self) -> str:
        return self.simple_category()

    def simple_category(self, max_iter=2) -> str:
        print("Thinking...")
        command: str = Task(
            f"I will give you a user query in natural language about Kubernetes. Your task is to transform the query into a valid kubectl command based on your knowledge. ONLY output the query (without any surrounding quotes) and nothing more. <user_query>{self.user_query}</user_query>.",
            self.team.main_agent).solve().content
        command = command.strip()
        if not command.startswith("kubectl"):
            command = explain_missing_kubectl(self.team, command)
        print(f"\nInitial kubectl command proposition: `{command}`\n")
        print("Validating command with output of 'kubectl help'...")

        k_nb_occurrences: int = command.count("kubectl")

        # get_help_task: Task = Task(
        #    f"I will give you an unknown string that may contain one or more kubectl commands. You must use the 'kubectl_help' tool for each kubectl command you find in that string. Your task is finished when the tool has been called on all kubectl commands. The string is <unknown_string>{command}</unknown_string>",
        #    self.team.k8s_help_agent,
        #    tools=[Tool("kubectl_help",
        #                "Outputs the syntax help from 'kubectl <action_verb> <resource_type> --help'.",
        #                get_cmd_help,
        #                usage_examples=[{"action_verb": "get", "resource_type": "deployment"}])])

        # print("-----------------------ALL HELP COMMANDS-----------------------")
        # print(get_help_task.solve().content)

        if k_nb_occurrences == 1:
            cmd_and_help = "$ " + command + "\n" + self.team.k8s_help_agent.history.get_last().content
        else:
            cmd_and_help = Task("Based on your previous answer. Aggregate the outputs of all kubectl commands and their associated help output. It should look like this : ```\n$ <kubectl_command>\n<help output from the tool>\n---\n$ <kubectl_command>\n<help output from the tool>\n```", self.team.k8s_help_agent).solve().content

        # print("############# command and help ###################")
        # print(cmd_and_help)
        # print("#############End command and help")

        Task(f"Your new task is to evaluate if the command{'s' if k_nb_occurrences > 1 else ''} you generated ('{command}') {'are' if k_nb_occurrences > 1 else 'is'} in accordance with the initial query of the user. I will provide the result of the associated 'kubectl <cmd> --help' in my next message. You must reflect on the command you chose and if it really matches the user's request.", self.team.main_agent).solve()
        Task(f"The query of the user was <user_query>{self.user_query}</user_query>.\nThe 'kubectl cmd --help' output of your chosen command{'s' if k_nb_occurrences > 1 else ''} is given bellow:\n{cmd_and_help}", self.team.main_agent).solve()

        if max_iter <= 0:
            return final_command_output(self.team, k_nb_occurrences)

        restart_flow_router: str = Task("To summarize your previous answer in one word. Do you need to rework the command you initially generated ? Answer ONLY by 'yes' or 'no'.", self.team.main_agent).solve().content
        if "yes" in restart_flow_router.lower():
            self.team.main_agent.history.add(Message(MessageRole.USER, "Okay, if the command you generated is not a perfect match we will start over the whole process from the beginning. Be sure not to make the same mistake twice."))
            self.team.main_agent.history.add(Message(MessageRole.SYSTEM, "Sure, let's start again. This time I will make sure to use the correct arguments and kubectl verbs using the knowledge I gained."))
            max_iter -= 1
            print("After reviewing 'kubectl help' I'm not happy with the proposed command. Let's try again.")
            return self.simple_category(max_iter=max_iter)
        else:
            return final_command_output(self.team, k_nb_occurrences)




