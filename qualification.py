from yacana import Task
from team import Team

query_qualification = [
    {
        'uid': 'general',
        'description': 'Asking for general kubernetes knowledge.',
        'ref': knowledge_category
    },
    {
        'uid': 'simple',
        'description': 'Simple query easily answered with only one kubectl command.',
        'ref': simple_category
    },
    {
        'uid': 'complex',
        'description': 'Complex query that might involve multiple kubectl commands, maybe bash syntax or even human input.',
        'ref': complex_category
    },
    {
        'uid': 'file',
        'description': 'Will definitely need a file to write YAML into and then maybe apply it.',
        'ref': file_category
    },
    {
        'uid': 'unrelated',
        'description': 'Has nothing to do with Kubernetes. Is off kubernetes topic.',
        'ref': unrelated_category
    }
]


def get_request_qualification(team: Team, max_iter: int = 4) -> str:
    uid_from_llm: str = Task(
        "To summarize your previous answer in one word. What was the category uid you chose. Only output the category uid.",
        team.assessment_agent).solve().content
    uid_from_llm = uid_from_llm.replace("'", "").replace('"', "")
    real_uid: str = next((qual["uid"] for qual in query_qualification if uid_from_llm.lower() in qual["uid"]), None)
    if max_iter <= 0:
        raise SystemExit("Reached max iteration during qualification")
    if real_uid is None:
        Task(
            f"You didn't only output one of the categories. You must choose one of {','.join([qual['uid'] for qual in query_qualification])} and output ONLY the category you chose.",
            team.assessment_agent).solve()
        max_iter -= 1
        real_uid = get_request_qualification(team, max_iter=max_iter)
    return real_uid

def qualify_request(team: Team):
    Task(
        f"I will give you the request of a user. You must qualify what the request is about and chose a category that best matches the query. The categories are defined in JSON : {query_qualification_stripped}.\nThe user's query is the following: <user_query>{user_query}</user_query>. In your opinion what category best matches the request ? Explain your reasoning.",
        team.assessment_agent).solve()
    uid: str = get_request_qualification(team)
