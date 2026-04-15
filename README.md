# sdlc-agent

## Overview
sdlc-agent is a full-stack application designed to streamline software development lifecycle processes. The backend integrates with Jira and GPT to provide automation and orchestration, while the frontend offers a user-friendly interface for managing tasks, generating responses, and more.

## Project Structure
```
.env                     # Root environment variables file
.gitignore               # Root gitignore
README.md                # Project documentation
requirements.txt         # Root Python dependencies (if any)

backend/                 # Backend services and logic
    .env.example         # Backend environment variables example
    .gitignore           # Backend gitignore
    README.md            # Backend documentation
    requirements.txt     # Backend dependencies
    agents/              # Agent implementations (ras, tcg)
        ras/
        tcg/
    common/              # Shared backend modules
        __init__.py
        ai_search/
        db/
        jira/
        llm/
        prompts/
        utils/
    DocIngestionFunction/        # Azure Function for document ingestion
        __init__.py
        function.json
    DurableFunctionsHttpStart/   # Azure Durable Functions HTTP starter
    DurableFunctionsOrchestrator/# Azure Durable Functions orchestrator
    ExecuteRAS/                  # RAS execution logic
    ExecuteTCG/                  # TCG execution logic
    PushtoJira/                  # Jira integration logic

frontend/                # Frontend (Streamlit-based) application
    .env                 # Frontend environment variables
    README.md            # Frontend documentation
    requirements.txt     # Frontend dependencies
    src/                 # Frontend source code
        app.py           # Main application entry point
        components/      # UI components and related logic
            buttons.py
            dialogs.py
            jira_auth.py
            rating.py
            response_gpt.py
            response_options.py
            sidebar.py
        services/        # Service-related logic
            jira_client.py
        utils/           # Utility functions and helpers
            css_loader.py
            excel_read.py
            session_manager.py
    static/              # Static assets
        image.jpg
        styles.css

static/                  # Project-level static assets (if any)
    image.jpg
    styles.css
```

## Installation

### Backend
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install frontend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Backend
- Start backend services as per the instructions in [backend/README.md](backend/README.md).

### Frontend
1. Run the Streamlit application:
   ```bash
   streamlit run src/app.py
   ```
2. Access the application in your browser at `http://localhost:8501`.

## Features
- **Jira Integration**: Authenticate and interact with Jira tasks.
- **GPT Responses**: Generate AI-driven responses using GPT.
- **Customizable UI**: Modify styles and components easily.
- **Session Management**: Maintain user sessions effectively.
- **Azure Functions**: Backend orchestration and automation.

## Contributing
1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add feature description"
   ```
4. Push to the branch:
   ```bash
   git push origin feature-name
   ```
5. Open a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.


