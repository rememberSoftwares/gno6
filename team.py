class Team:

    def __init__(self, main_agent, assessment_agent, logic_agent, k8s_help_agent):
        self.main_agent = main_agent
        self.assessment_agent = assessment_agent
        self.logic_agent = logic_agent
        self.k8s_help_agent = k8s_help_agent
