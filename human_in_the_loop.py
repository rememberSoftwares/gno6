import json

from yacana import Agent, Task, Message, MessageRole


def ask_for_help(agent: Agent, current_status: str, target_objective: str) -> str:
    print("It seems I am doing something wrong and need help to get back on track. Can you provide information on what is wrong ?")
    print("My target objective is : " + target_objective)
    print("However I'm currently generating this: " + current_status)
    print("Please asses the situation the best you can.")
    human_input: str = input("?> ")
    agent.history.add(Message(MessageRole.USER, "You are struggling to generate the correct answer. Let me help you get back on track."))
    agent.history.add(Message(MessageRole.ASSISTANT, "Okay thanks. Please help me solve my task correctly."))
    return Task(human_input, agent).solve().content

def ask_for_information(agent: Agent):
    Task("Based on the initial query, the knowledge that was accumulated and the kubectl help output, are there questions you would absolutely need to ask the user in order to fulfill its request?", agent).solve()
    must_ask_questions: str = Task("Was the answer of the previous question yes or no ? Only output 'yes' or 'no' and nothing else.", agent, forget=True).solve().content
    if "yes" in must_ask_questions.lower():
        json_questions_as_str: str = Task('Reformat your questions as a JSON array of strings where each array element is a question. For instance ["question1 ?", "question2 ?"]', agent, forget=True, json_output=True).solve().content
        json_questions: list[str] = json.loads(json_questions_as_str)
        print("I have a few questions for you to answer. If you don't know then say you don't know.")
        i = 0
        answers: list[str] = []
        for question in json_questions:
            print(f"{i}) {question}")
            answers.append(input("?>"))
            i += 1
        agent.history.add(Message(MessageRole.USER, map()))

