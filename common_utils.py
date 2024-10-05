from yacana import Task

from k8s_utils import explain_missing_kubectl
from team import Team


def final_command_output(team: Team, k_nb_occurrences: int) -> str:
    command = Task(
        f"Now that you have brainstormed and validated the command{'s' if k_nb_occurrences else ''}. Please output the final version. Only output the command{'s' if k_nb_occurrences else ''} and nothing else.",
        team.main_agent).solve().content
    if not command.startswith("kubectl"):
        command = explain_missing_kubectl(team)
    return command
