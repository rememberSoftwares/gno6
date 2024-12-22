from yacana import Agent, Message, MessageRole


class Memory:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Memory, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.facts = {}
            self.initialized = True

    def upsert(self, uid: str, fact: str) -> None:
        self.facts[uid] = fact

    def remove(self, uid: str) -> None:
        self.facts.pop(uid)

    def inject_all_facts(self, agent: Agent) -> None:
        formated_facts: str = "This is a list of facts I have gathered to help you answer the query:\n"
        for uid, fact in self.facts.items():
            formated_facts += "* " + fact + "\n"
        agent.history.add(Message(MessageRole.USER, formated_facts))
        agent.history.add(Message(MessageRole.ASSISTANT, "I will use the gathered facts to help me generate the correct output."))

    def inject_fact(self, agent: Agent, uid: str) -> None:
        if uid in self.facts:
            fact: str = self.facts[uid]
            formated_fact: str = f"This is a fact I have gathered to help you answer the query:\n* {fact}\n"
            agent.history.add(Message(MessageRole.USER, formated_fact))
            agent.history.add(Message(MessageRole.ASSISTANT, "I will use the gathered fact to help me generate the correct output."))
