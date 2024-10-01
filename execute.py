import subprocess

from yacana import Agent, Task



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


def execute_command_in_place_of_user(main_agent: Agent, k8s_cmd: str) -> bool:
    """

    :param main_agent:
    :param k8s_cmd:
    :return: bool : Success or failure
    """
    print("\nShould I execute the command for you?")
    should_execute: str = input("> ")
    router: str = Task(f"The user was asked a 'yes'/'no' question. Determine what was his choice and ONLY output 'yes' if it was affirmative else ONLY output 'no'. His answer: '{should_execute}'", main_agent, forget=True).solve().content
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