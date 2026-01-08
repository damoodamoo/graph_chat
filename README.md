# Graph Chat
This project explores running graph queries as LLM tool calls, as well as populating a graph as a materialised view from an event source.

## Getting Started

1. **Clone the repository**
    ```bash
    git clone https://github.com/damoodamoo/graph_chat.git
    cd graph_chat
    ```

2. **Open in dev container**
    - Open the project in VS Code
    - When prompted, click "Reopen in Container"
    - Or use Command Palette: `Dev Containers: Reopen in Container`

3. **Authenticate with Azure**
    ```bash
    az login
    ```

4. **Configure environment variables**
    - Create a `.env` file in the project root
    - Add required configuration (see `.env.example` if available)

5. **Deploy infrastructure**
    ```bash
    task infra:deploy
    ```

6. **Download source data from Kaggle**
    - Get a Kaggle API key and set it in .env
    ```bash
    task data:init
    task data:download
    ```

---

*This is an experimental project and may undergo significant changes.*