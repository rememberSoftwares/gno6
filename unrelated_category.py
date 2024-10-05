from yacana import Task

from category import Category
from team import Team


class UnrelatedCategory(Category):

    def __init__(self, user_query: str, team: Team):
        self.user_query = user_query
        self.team: Team = team

    def start_workflow(self) -> str:
        return self.unrelated_category()

    def unrelated_category(self) -> str:
        print("I acknowledge this information but won't output any kubectl commands. Still, I'll try to help you with your request.")
        return Task(f"{self.user_query}", self.team.main_agent).solve().content
