from typing_extensions import Callable
from yacana import Task

from CategoryFactory import CategoryFactory
from team import Team

query_qualification = [
    {
        'type': 'general',
        'description': 'Asking for general kubernetes knowledge.'
    },
    {
        'type': 'simple',
        'description': 'Simple query easily answered with only one kubectl command.'
    },
    {
        'type': 'complex',
        'description': 'Complex query that might involve multiple kubectl commands, maybe bash syntax or even human input.'
    },
    {
        'type': 'file',
        'description': 'Will definitely need a file to write YAML into and then maybe apply it.'
    },
    {
        'type': 'unrelated',
        'description': 'Has nothing to do with Kubernetes. Is off kubernetes topic.'
    }
]


def get_request_qualification(team: Team, max_iter: int = 4) -> str:
    type_from_llm: str = Task(
        "To summarize your previous answer in one word. What was the category type you chose. Only output the category type.",
        team.assessment_agent).solve().content
    type_from_llm = type_from_llm.replace("'", "").replace('"', "")
    type_from_json: str = next((qual["type"] for qual in query_qualification if type_from_llm.lower() in qual["type"]), None)
    if max_iter <= 0:
        raise SystemExit("Reached max iteration during qualification")
    if type_from_json is None:
        Task(
            f"You didn't only output one of the categories. You must choose one of {','.join([qual['type'] for qual in query_qualification])} and output ONLY the category you chose.",
            team.assessment_agent).solve()
        max_iter -= 1
        type_from_json = get_request_qualification(team, max_iter=max_iter)
    return type_from_json


def get_request_qualification_ref(request_type: str) -> Callable:
    CategoryFactory.get_category(request_type)
    return next((qual["ref"] for qual in query_qualification if qual["type"] == request_type), None)  # @todo check None


def qualify_request(team: Team, user_query: str) -> str:
    # Removing 'ref' field from the query_qualification JSON array
    query_qualification_stripped = [{k: v for k, v in item.items() if k != 'ref'} for item in query_qualification]
    Task(
        f"I will give you the request of a user. You must qualify what the request is about and chose a category that best matches the query. The categories are defined in JSON : {query_qualification_stripped}.\nThe user's query is the following: <user_query>{user_query}</user_query>. In your opinion what category best matches the request ? Explain your reasoning.",
        team.assessment_agent).solve()
    return get_request_qualification(team)
