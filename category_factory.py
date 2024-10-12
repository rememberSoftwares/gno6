from category import Category
from general_knowledge_category import GeneralKnowledgeCategory
from simple_category import SimpleCategory
from team import Team


class CategoryFactory:
    @staticmethod
    def get_category(category_type: str, user_query: str, team: Team) -> Category:
        if category_type == "general":
            return GeneralKnowledgeCategory(user_query, team)
        elif category_type == "simple":
            return SimpleCategory(user_query, team)
        elif category_type == "complex":
            return SimpleCategory(user_query, team)
        elif category_type == "file":
            raise NotImplemented("You requested file interactions like applying a Kubernetes manifest. This is not yet implemented. However we are working on it! ^^\nSorry for the inconvenience.")
        elif category_type == "unrelated":
            return SimpleCategory(user_query, team)
        else:
            raise ValueError(f"Category type {category_type} is not supported.")
