import os
import asyncio
import datetime
from dotenv import load_dotenv
from agents import Agent, Runner
from agents.exceptions import MaxTurnsExceeded
from agents.tracing import set_tracing_disabled

from searcher_tools import web_search, fetch_university_page, search_university_website
from calendar_tools import (
    add_calendar_event,
    update_calendar_event,
    remove_calendar_event,
    list_calendar_events,
    open_calendar,
)

load_dotenv()
set_tracing_disabled(True)

UNIVERSITY_NAME = os.getenv("UNIVERSITY_NAME", "the university")
STUDENT_INFO = os.getenv("STUDENT_INFO", "No additional student information provided.")

current_date = datetime.datetime.now().strftime("%Y-%m-%d")

# Instruction loader

def load_instructions(path: str, **kwargs):
    """Read a markdown instructions file and substitute {KEY} placeholders with values."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().format(**kwargs)

# Instructions

assistant_instructions = load_instructions(
    os.path.join(os.path.dirname(__file__), "agents", "assistant-agent.md"),
    UNIVERSITY_NAME=UNIVERSITY_NAME,
    STUDENT_INFO=STUDENT_INFO,
)

planner_instructions = load_instructions(
    os.path.join(os.path.dirname(__file__), "agents", "planner-agent.md"),
    CURRENT_DATE=current_date,
)

searcher_instructions = load_instructions(
    os.path.join(os.path.dirname(__file__), "agents", "searcher-agent.md"),
    UNIVERSITY_NAME=UNIVERSITY_NAME,
)

# Agents

SearcherAgent = Agent(
    name="Searcher Agent",
    handoff_description="Searches the web and university official pages for information, deadlines, and requirements.",
    instructions=searcher_instructions,
    tools=[search_university_website, fetch_university_page, web_search],
)

PlannerAgent = Agent(
    name="Planner Agent",
    handoff_description="Creates a step-by-step plan with real dates and manages the student's calendar.",
    instructions=planner_instructions,
    tools=[
        add_calendar_event,
        update_calendar_event,
        remove_calendar_event,
        list_calendar_events,
        open_calendar,
    ],
)

AssistantAgent = Agent(
    name="Assistant Agent",
    instructions=assistant_instructions,
    handoffs=[SearcherAgent, PlannerAgent],
)

#Main loop

async def main():
    print("=" * 60)
    print("\    /\ ")
    print(" )  ( ') hello!")
    print("(  /  )")
    print(" \(__)|")
    print("  Type your question and press Enter. Type 'quit' to exit.")
    print("=" * 60)

    history: list = []

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("Goodbye!")
            break

        # Build input: append new user message to existing history
        messages = history + [{"role": "user", "content": user_input}]

        print("\nAssistant: thinking...\n")
        try:
            result = await Runner.run(AssistantAgent, messages, max_turns=15)
            print(f"Assistant: {result.final_output}")
            history = result.to_input_list()
        except MaxTurnsExceeded:
            print("Assistant: I've been going back and forth too long on this one :( Could you simplify or rephrase your request?")


if __name__ == "__main__":
    asyncio.run(main())