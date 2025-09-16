from tools import medication_lookup_tool
from prompts import retrieve_agent_prompt
 
symptom_checker_agent = LLMAgent(
    name="langchain_tool_agent",
    model="gemini-2.0-flash",
    description="Agent to collect symptoms from the user.",
    instruction=retrieve_agent_prompt(f"symptom_collect")
)
 
medical_lookup_agent = Agent(
    name="langchain_tool_agent",
    model="gemini-2.0-flash",
    description="Agent to answer questions using TavilySearch.",
    instruction=retrieve_agent_prompt(f"medical_lookup"),
    tools=[medication_lookup_tool] # Add the wrapped tool here
)
 
code_pipeline_agent = SequentialAgent(
    name="SymptomAgent",
    sub_agents=[symptom_checker_agent, medical_lookup_agent],
    description="Executes a sequence of symptom collecting and medical lookup of symptoms.",
    # The agents will run in the order provided: Sypmtom Collect -> Medical Lookup
)