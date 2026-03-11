import questionary
from yacana import ToolError

# ANSI color codes for diffs (safe for terminals; if you return to an LLM UI that strips codes it's still fine)
ANSI_GREEN = "\x1b[32m"
ANSI_RED = "\x1b[31m"
ANSI_CYAN = "\x1b[36m"
ANSI_RESET = "\x1b[0m"
ANSI_BOLD = "\x1b[1m"

#CYAN = "\033[36m"
#RESET = "\033[0m"
#GREEN = "\033[32m"

def confirm_exec(question: str):
  while True:
    confirmed: bool = questionary.confirm(question).ask()
    if confirmed:
      break
    elif not confirmed:
      reason: str = questionary.text("Reason to give the LLM why you said no.").ask()
      raise ToolError(f"Tool was denied by the cluster admin with the following reason : {reason}")
