from yacana import Agent, LoggerManager, Message, MessageRole


class Team:

    def __init__(self, model: str, endpoint: str, logging_level, namespace: str | None):
        main_agent = Agent("main_agent", model,
                           system_prompt="You are a helpful AI assistant expert on kubectl commands and kubernetes clusters. Your end goal is to generate a valid kubectl command based on the user query.", endpoint=endpoint)
        assessment_agent = Agent("Assessment_agent", model,
                                 system_prompt="You are an AI assistant with the goal to qualify user requests into predefined categories.", endpoint=endpoint)
        logic_agent = Agent("Logic_agent", model,
                            system_prompt="You are an AI assistant that reflects on other's problematic by asking question and ensuring that the response given in return is logic.", endpoint=endpoint)
        k8s_help_agent = Agent("K8s_validator", model,
                               system_prompt="You are an AI assistant that can access kubectl command line help. You make sure that kubectl commands are valid and help refacto them if needed.", endpoint=endpoint)
        LoggerManager.set_log_level(None if logging_level == "None" else logging_level)

        if namespace is not None:
            main_agent.history.add(Message(MessageRole.USER, f"Targeted Kubernetes namespace is {namespace}"))
            main_agent.history.add(Message(MessageRole.ASSISTANT, f"Okay! Now on, all Kubernetes commands should set this argument: '-n {namespace}'"))

        self.main_agent = main_agent
        self.assessment_agent = assessment_agent
        self.logic_agent = logic_agent
        self.k8s_help_agent = k8s_help_agent

    def reset(self):
        self.main_agent.history.pretty_print()
        self.main_agent.history.clean()
        self.assessment_agent.history.clean()
        self.logic_agent.history.clean()
        self.k8s_help_agent.history.clean()
        # if we keep that we loose the knowledge history. So maybe the function that treats this part should be added to the main_agent after the clean
