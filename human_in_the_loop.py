import json
import os
from typing import List

from yacana import Agent, Task, Message, MessageRole

from execute import exec_kubectl_cmd
from memory import Memory


def ask_for_help(agent: Agent, current_status: str, target_objective: str) -> str:
    print("It seems I am doing something wrong and need help to get back on track. Can you provide information on what is wrong ?")
    print("My target objective is : " + target_objective)
    print("However I'm currently generating this: " + current_status)
    print("Please asses the situation the best you can.")
    human_input: str = input("?> ")
    agent.history.add(Message(MessageRole.USER, "You are struggling to generate the correct answer. Let me help you get back on track."))
    agent.history.add(Message(MessageRole.ASSISTANT, "Okay thanks. Please help me solve my task correctly."))
    return Task(human_input, agent).solve().content


def check_information_presence(agent: Agent, query: str) -> None:
    checkpoint: str = agent.history.create_check_point()
    agent.history.add(Message(MessageRole.USER, f"I give you a kubernetes related query. Next I will ask you questions about that query. Query: '{query}'"))
    agent.history.add(Message(MessageRole.ASSISTANT, "I understand. What questions should I answer about this query ?"))

    memory = Memory()
    if_info_not_found: str = " else output 'unknown' and nothing else."
    information: List[str] = [
        "Does the request specifies a namespace ? If it does, output the namespace name ONLY"
    ]
    # Pour le moment c'est un tableau mais ca ne sert à rien car je met la clé "namespace" en dur dans la mémoire. Après je pourrais faire une map au dessus.

    for info in information:
        llm_result: str = Task(info + if_info_not_found, agent).solve().content
        print(f"LLM result : {llm_result}")
        if "unknown" in llm_result.lower():
            print("It seems you didn't specify a namespace. I'll list all the current namespaces you have access and let you choose one. Please type the namespace this request should apply to.")
            input("Press any key to continue...")
            output: str = exec_kubectl_cmd("kubectl get namespaces")
            print(output)
            ns: str = input("What namespace should I use ?\n>")
            memory.upsert("namespace", f'Current namespace is: {ns}')
    agent.history.load_check_point(checkpoint)


def look_for_missing_information(agent: Agent, query: str) -> None:
    memory = Memory()
    checkpoint: str = agent.history.create_check_point()
    agent.history.add(Message(MessageRole.USER, f"I give you a kubernetes related query. Next I will ask you questions about that query. Query: '{query}'"))
    agent.history.add(Message(MessageRole.ASSISTANT, "I understand. What questions should I answer about this query ?"))

    Task("Based on the initial query, the accumulated knowledge and the kubectl help output, are there any missing contextual questions you would absolutely need to ask the user in order to fulfill its request? Note that you already know what kubectl command to use.", agent).solve()
    print("blabla = " + agent.history.get_last().content)
    must_ask_questions: str = Task("Was the answer of the previous question yes or no ? Only output 'yes' or 'no' and nothing else.", agent, forget=True).solve().content
    print(f"Must ask questions : {must_ask_questions}")
    if "yes" in must_ask_questions.lower():
        print("it was a yes")
        print("If you don't know the answer to a question, press enter and leave the field empty.")
        questions: str = Task('Reformat your questions as a minimalistic list.', agent).solve().content
        i = 0
        for question in questions.split("\n"):
            answer = input(f"{question}\n?> ")
            if answer.strip():
                memory.upsert(f"contextual_info-{i}", f"Question: {question}\nAnswer: {answer}")
            i += 1
    agent.history.load_check_point(checkpoint)
