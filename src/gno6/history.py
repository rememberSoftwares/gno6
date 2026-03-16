def compact_history(agent):
    recap: str = (
        Task(
            """Let's recap all steps that you went through and their associated results. To do so create an ordered list following this format:
* 1) <Subtask title>
Command: `<kubectl command that was done>`
Relevant ouput:
```
<Meaningful output from the command. Only keep what is relevant.>
```
Conclusion: <Conclusions from the output>

---

Example when looking for a resource:
* 1) Looking for target pod.
Command `kubectl get pod -n mynamespace`
Relevant output:
```
NAME        READY   STATUS    RESTARTS   AGE
my-pod      1/1     Running   0          12d
```
Conclusion: Pod has been found in namespace mynamespace and is running.

---

Example with a `kubectl logs`:
* 1) Searching for root cause inside logs of pod my-pod.
Command: `kubectl logs my-pod -n mynamespace`
Meaningful output:
```
14:00-Booting app
14:00-OutOfMemory exception
```
Conclusion: Logs show that the Pod may be running out of memory.

---

Final instructions: Do not make things up. Ground your answer based on this conversation.
""",
            agent,
        )
        .solve()
        .content
    )
    tagged_messages = agent.history.get_messages_by_tags("kubectl")
    for tagged_msg in tagged_messages:
        agent.history.delete_message(tagged_msg)
    agent.history.pretty_print()
    agent.history.add_message(
        Message(
            MessageRole.USER,
            "Let's recap all operations that have already be done.",
            ["compact"],
        )
    )
    agent.history.add_message(Message(MessageRole.ASSISTANT, recap, ["compact"]))
    print("------------------------------")
    agent.history.pretty_print()

