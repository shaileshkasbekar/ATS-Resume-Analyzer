"""
Agentic AI layer (Career Agent).

The existing resume_parser functions are exposed to the LLM as tools.
Specialist agents choose and call those tools in a loop, and a LangGraph
workflow decides which agents to run for the user's goal.

    tools.py        existing functions wrapped as LLM tools
    llm.py          the tool-calling loop (think -> call tool -> observe)
    specialists.py  the five agents: role, instructions, allowed tools
    graph.py        LangGraph workflow: memory -> plan -> agents -> answer
    memory.py       long-term career memory per user
    tracking.py     execution trace (runs and steps)
"""
