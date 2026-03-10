# University Multi-Agent Planner

A **multi-agent system** designed to help students plan and execute university-specific tasks. The system consists of three agents:

- **Assistant Agent** – interacts with the user, gathers context, and provides personalized guidance.  
- **Planner Agent** – creates structured plans and roadmaps based on user goals.  
- **Searcher Agent** – finds relevant information from official sources (university websites) or general web sources if necessary.  

Together, these agents form a **planner system** that can assess student goals, generate actionable steps, and output them in structured formats.

---

## Features

- **Goal Assessment**: Understands user objectives and what they want to achieve.  
- **Context-Aware Assistance**: The assistant can use background information about the student to provide more tailored advice.  
- **Official Web Search**: The searcher agent retrieves information from university websites or general sources depending on the query.  
- **Automated Planning**: Generates structured plans and roadmaps considering the current date.  
- **Calendar Integration**: Adds approved plans to a `calendar.html` file, which can be viewed directly in a browser.  

---

## Getting Started

### Prerequisites

- Python 3.10+  
- API keys for web search (Tavily or similar) and AI model

### Installation

1. Clone the repository:

```bash
git clone https://github.com/begonil17/planner-agent.git
cd planner-agent
```

2. Install required packages
```bash
pip install -r requirements.txt
```

3. Add your environment variables (.env file) for:
  - `TAVILY_API_KEY` – for web search
  - `OPENAI_API_KEY` – API key for accessing the AI model
  - `UNIVERSITY_NAME` – the name of the university
  - `UNIVERSITY_URL_PATTERN` – the official university URL pattern (for restricted searches)
  - `STUDENT_INFO` – optional background information about the student

## Running the Agents
Run the main script
```bash
python agents.py
```

## References

This project was implemented following OpenAI’s agent documentation:
- [A Practical Guide to Building Agents](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- [OpenAI Python Agents Quickstart](https://openai.github.io/openai-agents-python/quickstart/)
  

> Note: This project uses external APIs (OpenAI, Tavily). You must obtain your own API keys and comply with their respective terms of service.
