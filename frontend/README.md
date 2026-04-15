# sdlc-agent

## Overview
sdlc-agent is a Streamlit-based application designed to streamline software development lifecycle processes. It integrates with Jira and GPT to provide a seamless user experience for managing tasks, generating responses, and more.

## Project Structure
```
.env                     # Environment variables file
.streamlit/              # Streamlit configuration folder
    config.toml          # Streamlit configuration file
requirements.txt         # Python dependencies file
src/                     # Source code folder
    app.py               # Main application entry point
    components/          # UI components and related logic
        buttons.py       # Button-related components
        dialogs.py       # Dialog-related components
        jira_auth.py     # Jira authentication logic
        rating.py        # Rating-related components
        response_gpt.py  # GPT response handling
        response_options.py # Response options logic
        sidebar.py       # Sidebar-related components
    services/            # Service-related logic
        jira_client.py   # Jira client implementation
    utils/               # Utility functions and helpers
        css_loader.py    # CSS loading utility
        excel_read.py    # Excel reading utility
        session_manager.py # Session management utility
static/                  # Static assets
    image.jpg            # Example image asset
    styles.css           # CSS styles for the application
```

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```bash
   cd sdlc-agent
   ```
3. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
1. Run the application:
   ```bash
   streamlit run src/app.py
   ```
2. Access the application in your browser at `http://localhost:8501`.

## Features
- **Jira Integration**: Authenticate and interact with Jira tasks.
- **GPT Responses**: Generate AI-driven responses using GPT.
- **Customizable UI**: Modify styles and components easily.
- **Session Management**: Maintain user sessions effectively.

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
