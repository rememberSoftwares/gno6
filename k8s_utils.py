from yacana import GroupSolve, Task, EndChat, EndChatMode, Agent, Message, MessageRole

from team import Team
from tools import call_kubectl_cmd


def explain_missing_kubectl(team: Team) -> str:
    GroupSolve(
        [Task("It seems like the command you outputted doesn't start with 'kubectl'. Is this normal ?", team.main_agent),
         Task(
             "A kubectl command was created to match the query of a user. However the command did not start with 'kubectl' which seems strange. Investigate why. You task is done when you are sure that the command starts with 'kubectl'.",
             team.logic_agent, llm_stops_by_itself=True)],
        EndChat(EndChatMode.END_CHAT_AFTER_FIRST_COMPLETION, max_iterations=2)).solve()
    final_cmd: str = Task(
        "After deliberation what is the final kubectl command ? Only output the command and NOTHING ELSE",
        team.main_agent).solve().content
    return final_cmd


def add_minimal_k8s_help_to_history(main_agent: Agent) -> None:
    all_k8s_cmds: str = call_kubectl_cmd("kubectl --help")
    main_agent.history.add(Message(MessageRole.USER,
                              "To help you answer kubectl related questions I give you the kubectl --help output bellow:\n" + all_k8s_cmds))
    main_agent.history.add(Message(MessageRole.ASSISTANT,
                              "Okay thank you. I will use this piece of information to ground my answers and help me chose the correct kubectl action."))
