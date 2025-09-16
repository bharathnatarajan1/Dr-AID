from subagents.tools import medication_lookup_tool
from prompts import retrieve_agent_prompt
from google.adk.agents import LlmAgent,Agent,SequentialAgent
from common import MODEL
 
symptom_checker_agent = LlmAgent(
    name="langchain_tool_agent",
    model=MODEL,
    description="Agent to collect symptoms from the user.",
    instruction=retrieve_agent_prompt(f"symptom_collect")
)
 
medical_lookup_agent = LlmAgent(
    name="langchain_tool_agent",
    model=MODEL,
    description="Agent to answer questions using TavilySearch.",
    instruction=retrieve_agent_prompt(f"medical_lookup"),
    tools=[medication_lookup_tool] # Add the wrapped tool here
)
 
symptom_agent = SequentialAgent(
    name="SymptomAgent",
    sub_agents=[symptom_checker_agent, medical_lookup_agent],
    description="Executes a sequence of symptom collecting and medical lookup of symptoms.",
    # The agents will run in the order provided: Sypmtom Collect -> Medical Lookup
)