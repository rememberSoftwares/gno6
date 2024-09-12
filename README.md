# Gno6 - alpha
Translating human input as kubectl commands using LLMs powered by [Yacana](https://remembersoftwares.github.io/yacana/)

![Gno6_medium](https://github.com/user-attachments/assets/5d2b2402-18d4-4e81-874a-01d16ef4f1b3)

**gno6** is a powerful tool designed to translate natural language queries into valid `kubectl` commands. It leverages a self-correcting mechanism based on the output of `kubectl help`, ensuring high accuracy without relying solely on LLM (Large Language Model) training.

By combining the flexibility of multi-agent frameworks and robust tool-calling capabilities, **gno6** offers an innovative approach to Kubernetes command automation. The tool operates locally, powered by **[Yacana](https://remembersoftwares.github.io/yacana/)**, a multi-agent framework that integrates seamlessly with any LLM, and requires **Ollama** for running the model on your own machine.

---

## Key Features

- **Natural Language to kubectl**: Easily converts user queries into actionable `kubectl` commands.
- **Self-Correction**: Uses `kubectl help` to refine and propose accurate commands.
- **Multi-Agent Architecture**: Built on **Yacana**, allowing for distributed task execution and tool calling.
- **Local Deployment**: Runs entirely on your machine with Ollama as a requirement, keeping your workflows private and efficient.
  
---

## Installation

1. Install [Ollama](https://ollama.com) to enable local LLM execution.
   
2. Clone the repository:
 ```bash
   git clone https://github.com/RememberSoftwares/gno6.git
   cd gno6
```

3. Install the required dependencies:
```bash
   pip install -r requirements.txt
```

---

## Usage

Once installed, you can begin translating natural language queries into Kubernetes commands:

```bash
python gno6.py
```

Provide a query, and gno6 will return the corresponding `kubectl` command.

Example:
```
User: Show me all running pods in the dev namespace.
gno6: kubectl get pods -n dev --field-selector=status.phase=Running
```

### Options

- **Command Preview**: gno6 provides the command it intends to execute, allowing you to review before running.
- **Self-Help Adjustment**: The tool analyzes `kubectl help` to fine-tune its suggestions and minimize errors.

---

## Why Use gno6?

- **Accuracy**: By leveraging `kubectl help`, the tool avoids common pitfalls and adapts to new `kubectl` releases.
- **Efficiency**: No need to memorize or look up `kubectl` commands—just ask in natural language.
- **Local Execution**: Full control over your environment with the added privacy of running the model locally.

---

## Contributing

Contributions are welcome! If you'd like to improve **gno6** or suggest new features, feel free to open a pull request or submit an issue.

---

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for more details.

---

## Acknowledgements

Special thanks to:
- The **Yacana** framework for enabling multi-agent collaboration.
- The **Ollama** team for providing the infrastructure to run LLMs locally.
