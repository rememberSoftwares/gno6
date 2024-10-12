from yacana import GroupSolve, Task, EndChat, EndChatMode, Agent, Message, MessageRole

from human_in_the_loop import ask_for_help
from team import Team
from tools import call_kubectl_cmd
from itertools import takewhile


def explain_missing_kubectl(team: Team, command: str, recursion=2) -> str:
    # Using RECURSION to check if after finishing the first run of this function the issue is solved
    if command.startswith("kubectl"):
        print("the fuck 1")
        return command

    if recursion <= 0:
        print("the fuck 2")
        ask_for_help(team.main_agent, f"Current kubectl command is: [{command}] (the '[]' are hardcoded and are not part of the LLM output so don't take them into account)", "The objective is to generate a VALID kubectl command that must START with kubectl. It seems that the command doesn't start with kubectl and can't figure why.")

    try:
        print("the fuck 3")
        if command.startswith("`") or command.startswith("\"") or command.startswith("\'"):
            return strip_quotes(team, command)
    except ValueError:
        checkpoint: str = team.main_agent.history.create_check_point()
        GroupSolve(
            [Task("It seems like the command you outputted doesn't start with 'kubectl'. Is this normal ?", team.main_agent),
             Task(
                 "A kubectl command was created to match the query of a user. However the command did not start with 'kubectl' which seems strange. Investigate why. You task is done when you are sure that the command starts with 'kubectl'.",
                 team.logic_agent, llm_stops_by_itself=True)],
            EndChat(EndChatMode.END_CHAT_AFTER_FIRST_COMPLETION, max_iterations=2)).solve()
        final_cmd: str = Task(
            "After deliberation what is the final kubectl command ? Only output the command and NOTHING ELSE",
            team.main_agent).solve().content
        team.main_agent.history.load_check_point(checkpoint)
        team.main_agent.history.add(Message(MessageRole.USER, "It seems like the command you outputted doesn't start with 'kubectl'. Please correct the command."))
        team.main_agent.history.add(Message(MessageRole.ASSISTANT, final_cmd))
        recursion -= 1
        print("the fuck 4")
        return explain_missing_kubectl(team, final_cmd, recursion)


def strip_quotes(team: Team, command: str) -> str:
        new_cmd: str = Task("It seems that the command you generated starts with a quote. Please generate this same command WITHOUT surrounding quotes. I only need the raw kubectl command and nothing else.", team.main_agent).solve().content
        print(f"kek il en pense michel ? {new_cmd}")
        # Counting the number of quotes that starts the string
        if len(list(takewhile(lambda x: x in "'\"`", new_cmd))) <= 0 and new_cmd.startswith("kubectl"):
            print(f"on utilise la nouvelle fonction")
            return new_cmd
        else:
            raise ValueError("LLM failed to remove quotes")


def add_minimal_k8s_help_to_history(main_agent: Agent) -> None:
    all_k8s_cmds: str = call_kubectl_cmd("kubectl --help")
    main_agent.history.add(Message(MessageRole.USER,
                                   "To help you answer kubectl related questions I give you the kubectl --help output bellow:\n" + all_k8s_cmds))
    main_agent.history.add(Message(MessageRole.ASSISTANT,
                                   "Okay thank you. I will use this piece of information to ground my answers and help me chose the correct kubectl action."))
