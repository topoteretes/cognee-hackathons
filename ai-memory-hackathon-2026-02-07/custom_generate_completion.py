from typing import Optional, Type, Any
from cognee.infrastructure.llm.LLMGateway import LLMGateway
from cognee.infrastructure.llm.prompts import read_query_prompt


async def generate_structured_completion_with_user_prompt(
    user_prompt: str,
    system_prompt_path: str,
    system_prompt: Optional[str] = None,
    conversation_history: Optional[str] = None,
    response_model: Type = str,
) -> Any:
    """Generates a structured completion using LLM with given context and prompts."""
    system_prompt = system_prompt if system_prompt else read_query_prompt(system_prompt_path)

    if conversation_history:
        #:TODO: I would separate the history and put it into the system prompt but we have to test what works best with longer convos
        system_prompt = conversation_history + "\nTASK:" + system_prompt

    return await LLMGateway.acreate_structured_output(
        text_input=user_prompt,
        system_prompt=system_prompt,
        response_model=response_model,
    )


async def generate_completion_with_user_prompt(
    user_prompt: str,
    system_prompt_path: str,
    system_prompt: Optional[str] = None,
    conversation_history: Optional[str] = None,
) -> str:
    """Generates a completion using LLM with given context and prompts."""
    return await generate_structured_completion_with_user_prompt(
        user_prompt=user_prompt,
        system_prompt_path=system_prompt_path,
        system_prompt=system_prompt,
        conversation_history=conversation_history,
        response_model=str,
    )
