# Gno6 - alpha
A kubernetes agent that yields kubectl. Powered by [Yacana](https://remembersoftwares.github.io/yacana/)

<p align="center">
  <img src="https://github.com/user-attachments/assets/5d2b2402-18d4-4e81-874a-01d16ef4f1b3">
</p>

**This software is work in progress! Stay tuned!**

Gno6 is a powerful Kubernetes agent design to investigate and fix issues on your behalf.  
Investigation is automatic but requires human validation for any command that is not about getting/listing resources.  
It should be safe to use anywhere but refrain from using this on any production clusters before we get to beta.

---

## Key Features

- **Kubernetes based workflows**: Built specificaly for kubernetes needs. This agent already knows the steps to debug clusters. Ask it anything and it will start working while you drink mojitos.
- **Automatic kubectl command apply**: Don't need to paste kubectl commands from chatGPT. The LLM will make it's own commands and use the output accordingly.
- **Asks user when question arises**: When the LLM is unsure how to proceed or needs some piece of information, it will ask you directly.
- **File system access**: Can search, read and write files so you can work with your local helm charts.  
- **scripts and helm exec**: Can exec scripts or use helm binary to interact with your cluster.  
---

## Requirements

* Python3
* LLM endpoint (OpenAI or Ollama)

## Installation

1. **Clone the repository:**  
```bash
git clone https://github.com/RememberSoftwares/gno6.git
cd gno6
```

2. **Install pipx or UV (You really should be using UV !)**

[UV install](https://docs.astral.sh/uv/getting-started/installation/)  

or  
```
# Install pipx:
sudo apt install pipx
```

3. **Install Gno6:**
```
# Using UV
uv tool install . --python 3.12

# Using pipx
pipx install .
```

4. **Run:**  
```
gno6
```

⚠️ Python3.14 is not supported because of Pydantic. If you don't want to downgrade your whole system, use UV ! It will deal with python versions for you.


## Upgrading

1. Pull the lastest changes using git  
2. Uninstall current version of the tool: `uv tool uninstall gno6`  
3. Reinstall the tool: `uv tool install .`  

If the version doesn't update then uninstall and try `uv cache clean` before reinstalling the tool.  

---

## Configuration

**Starting the CLI will auto generate these variables so you don't have to set them yourself. Still, here they are...**

### **Mandatory** ENV variables:  

* Set LLM endpoint and creds
```bash
export GNO6_ENDPOINT=<endpoint>
export GNO6_API_KEY=<api_key>
export GNO6_MODEL=<model_name>
```

*Endpoint should end with `/v1` if using openai.*  

### **Optionnal** ENV variables:  

* Set logging levels
```
export GNO6_LOG_LEVEL=<log_levev>
```
Available values are *DEBUG*, *INFO* and *WARNING* (default)

* Set llm API type
```
export GNO6_ENDPOINT_PROVIDER=<provider>
```
Available values are *openai*(default) and *ollama* (untested for now)  

## Roadmap

* Add window size attention
* Keep conversations history
* Use a config file instead of ENV

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for more details.

## Disclaimer

This software is delivered as is and I couldn't be held responsible for any problem it may create.
