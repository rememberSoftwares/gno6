# Gno6 - alpha
A kubernetes agent that yields kubectl. Powered by [Yacana](https://remembersoftwares.github.io/yacana/)

<p align="center">
  <img src="https://github.com/user-attachments/assets/5d2b2402-18d4-4e81-874a-01d16ef4f1b3">
</p>

**This software is work in progress! Stay tuned!**

**gno6** is a powerful tool designed to translate natural language queries into kubernetes workflows.  
You can ask gno6 to investigate any buggy resource and to fix it.  
Investigation is automatic but requires human validation for any command that is not about getting/listing resources.  
It should be safe to use anywhere but refrain from using this on any production clusters anyway.

---

**This software needs an unpublished version of Yacana. Update will come shortly.**

## Key Features

- **Kubernetes based workflows**: Built specificaly for kubernetes needs. This agent already knows the steps to debug clusters. Ask it anything and it will start working while you drink mojito.
- **Automatic kubectl command apply**: Don't need to paste your own kubectl outputs into chatGPT. The LLM will make it's own commands and use the output accordingly.
- **Asks user when question arises**: When the LLM is unsure how to proceed or needs some piece of information, it will ask you directly.

---

## Requirements

* Python3
* LLM endpoint (OpenAI or Ollama)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/RememberSoftwares/gno6.git
cd gno6
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

To get faster dependy build you should be using [uv](https://docs.astral.sh/uv/getting-started/installation/).

---

## Usage

**Mandatory** ENV variables:  

```bash
export GNO6_ENDPOINT=<endpoint>
export GNO6_API_KEY=<api_key>
export GNO6_MODEL=<model_name>
```

*Endpoint should end with `/v1` if using openai.*

**Optionnal** ENV variables:  
```
export GNO6_LOG_LEVEL=<log_levev>
```
Available values are *DEBUG*, *INFO* (default) and *WARNING*

```
export GNO6_ENDPOINT_PROVIDER=<provider>
```
Available values are *openai*(default) and *ollama* (untested for now)

Once installed, you can start gno6 with  `python3 gno6.py`:


## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for more details.

## Disclaimer

This software is delivered as is and I couldn't be held responsible for any problem it may create.
