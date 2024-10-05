from yacana import Task

from category import Category
from team import Team


class GeneralKnowledgeCategory(Category):

    def __init__(self, user_query: str, team: Team):
        self.user_query = user_query
        self.team: Team = team

    def start_workflow(self) -> str:
        return self.general_knowledge_category()

    def general_knowledge_category(self) -> str:
        print("The request was considered as general knowledge and no command will be proposed. I will "
              "still try to answer your question.")
        return Task(f"{self.user_query}", self.team.main_agent).solve().content
