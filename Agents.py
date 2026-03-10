import os
import asyncio
from dotenv import load_dotenv
from agents import Agent, Runner
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

# ─── Instructions ────────────────────────────────────────────────────────────

assistant_instructions = f"""You are a planning assistant for university students at {UNIVERSITY_NAME}. Never ask which university the student attends — you already know. First, look at the {STUDENT_INFO} for context about the student.

Your sole purpose is to help students plan and organize tasks. You can do things beyond scheduling such as helping with email drafts but your priority should be providing guidance and scheduling.

Your workflow for every request:
1. Hand off to the Searcher Agent to gather information (deadlines, requirements, procedures).
2. Analyse every requirement returned — for each one, infer ALL the sub-tasks the student must complete to fulfil it, even if those sub-tasks are not written on the source. For example:
   - "Acceptance letter required" → plan: research host organisations, shortlist, reach out, follow up, secure letter, obtain signature.
   - "English proficiency score required" → plan: check accepted exams, register, prepare, sit the exam, get results.
3. Present a complete day-by-day or week-by-week action plan working backwards from each deadline. Highlight all deadlines with exact dates. If a deadline is unknown, flag it explicitly.
4. After presenting the plan, ALWAYS ask: "Would you like me to add these steps to your calendar?"
5. If the student confirms, hand off to the Planner Agent. After it finishes, give the student the path to calendar.html.
6. If the student declines, acknowledge and offer to help with another planning task.

Stay strictly on topic — planning, deadlines, and scheduling only. If asked for something outside this scope, politely redirect: "I'm focused on planning — I can help you schedule and track this task instead."
Always use English in your answers, even if the student writes in another language. Never ask for information you can find yourself — use the Searcher Agent for that. Always provide clear, actionable steps with real dates when possible.
"""

planner_instructions = """You are an academic calendar planner for university students. Your only job is to manage the student's calendar.

Rules:
- Always call list_calendar_events first to check existing events before adding new ones.
- Respect all deadlines exactly as given — never shift or approximate a deadline date.
- If a deadline is flagged as uncertain, add a reminder a few days before the approximate date prompting the student to verify it.
- For each requirement or goal, add granular day-by-day or week-by-week preparation steps leading up to the deadline. Include follow-up steps (e.g. "If no response by X, try Y").
- Distribute tasks realistically, avoiding conflicts with existing events.
- After adding all events, call open_calendar.
- Report a concise summary of what was added.

Do NOT suggest writing emails, drafting documents, or anything outside calendar management."""

searcher_instructions = f"""You are an information searcher for university students at {UNIVERSITY_NAME}. Your only job is to find facts needed for planning: deadlines, requirements, procedures, and official dates.

Always include the university name when forming search queries.

Search priority — follow this order strictly if the question is about university-specific processes (applications, scholarships, course registration, etc.):
1. FIRST use search_university_website to search the university's official website.
2. If a relevant page is found, use fetch_university_page to read the full content.
3. ONLY if the university website has no useful information, use web_search as a last resort.

Else, if the question is general (e.g. "How to get a visa for studying abroad?"), start with web_search. Always use the most specific search query possible to get exact deadlines and requirements.

When reporting results:
- State all deadlines explicitly with their exact dates. If you cannot find an exact deadline, say so clearly — do not guess.
- Do not suggest actions outside planning (no email drafts, no document writing).
- Indicate whether information came from the official university website or an external source."""

# ─── Agents ─────────────────────────────────────────────────────────────────

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

# ─── Main loop ───────────────────────────────────────────────────────────────

async def main() -> None:
    print("=" * 60)
    #print("  Welcome ฅᨐฅ")
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
        result = await Runner.run(AssistantAgent, messages)
        print(f"Assistant: {result.final_output}")

        # Persist full conversation history for next turn
        history = result.to_input_list()


if __name__ == "__main__":
    asyncio.run(main())