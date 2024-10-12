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