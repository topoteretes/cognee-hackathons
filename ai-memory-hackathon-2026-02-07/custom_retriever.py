import asyncio
import pathlib
import os
from typing import Optional, Type, List
from uuid import NAMESPACE_OID, uuid5

from cognee.infrastructure.engine import DataPoint
from cognee.modules.graph.cognee_graph.CogneeGraphElements import Edge
from cognee.modules.retrieval.graph_completion_retriever import GraphCompletionRetriever
from cognee.tasks.storage import add_data_points
from cognee.modules.graph.utils import resolve_edges_to_text
from cognee.modules.graph.utils.convert_node_to_data_point import get_all_subclasses
from cognee.modules.retrieval.utils.brute_force_triplet_search import brute_force_triplet_search
from cognee.modules.retrieval.utils.completion import summarize_text
from cognee.modules.retrieval.utils.session_cache import (
    save_conversation_history,
    get_conversation_history,
)
from cognee.shared.logging_utils import get_logger
from cognee.modules.retrieval.utils.extract_uuid_from_node import extract_uuid_from_node
from cognee.modules.retrieval.utils.models import CogneeUserInteraction
from cognee.modules.engine.models.node_set import NodeSet
from cognee.infrastructure.databases.graph import get_graph_engine
from cognee.context_global_variables import session_user
from cognee.infrastructure.databases.cache.config import CacheConfig
from custom_generate_completion import generate_completion_with_user_prompt
from cognee.infrastructure.llm.prompts.render_prompt import render_prompt

logger = get_logger("GraphCompletionRetrieverWithUserPrompt")

class GraphCompletionRetrieverWithUserPrompt(GraphCompletionRetriever):
    """
    Retriever for handling graph-based completion searches, with a given filename
    for the user prompt.

    This class inherits from the GraphCompletionRetriever and provides all of its methods,
    with get_completion being slightly modified.
    """

    def __init__(
        self,
        user_prompt_filename: str,
        system_prompt_path: str = "answer_simple_question.txt",
        system_prompt: Optional[str] = None,
        top_k: Optional[int] = 5,
        node_type: Optional[Type] = None,
        node_name: Optional[List[str]] = None,
        save_interaction: bool = False,
    ):
        """Initialize retriever with prompt paths and search parameters."""
        super().__init__(
            save_interaction = save_interaction,
            system_prompt_path = system_prompt_path,
            system_prompt = system_prompt,
            top_k = top_k if top_k is not None else 5,
            node_type = node_type,
            node_name = node_name,
        )
        self.user_prompt_filename = user_prompt_filename

    async def get_completion(
        self,
        query: str,
        context: Optional[List[Edge]] = None,
        session_id: Optional[str] = None,
    ) -> List[str]:
        """
        Generates a completion using graph connections context based on a query.

        Parameters:
        -----------

            - query (str): The query string for which a completion is generated.
            - context (Optional[Any]): Optional context to use for generating the completion; if
              not provided, context is retrieved based on the query. (default None)
            - session_id (Optional[str]): Optional session identifier for caching. If None,
              defaults to 'default_session'. (default None)

        Returns:
        --------

            - Any: A generated completion based on the query and context provided.
        """
        triplets = context

        if triplets is None:
            triplets = await self.get_context(query)

        context_text = await resolve_edges_to_text(triplets)

        cache_config = CacheConfig()
        user = session_user.get()
        user_id = getattr(user, "id", None)
        session_save = user_id and cache_config.caching

        user_prompt = render_prompt(
            filename=self.user_prompt_filename,
            context={"question": query, "context": context_text},
            base_directory=str(pathlib.Path(
            os.path.join(pathlib.Path(__file__).parent, "prompts")).resolve())
        )

        if session_save:
            conversation_history = await get_conversation_history(session_id=session_id)

            context_summary, completion = await asyncio.gather(
                summarize_text(context_text),
                generate_completion_with_user_prompt(
                    user_prompt=user_prompt,
                    system_prompt_path=self.system_prompt_path,
                    system_prompt=self.system_prompt,
                    conversation_history=conversation_history,
                ),
            )
        else:
            completion = await generate_completion_with_user_prompt(
                user_prompt=user_prompt,
                system_prompt_path=self.system_prompt_path,
                system_prompt=self.system_prompt,
            )

        if self.save_interaction and context and triplets and completion:
            await self.save_qa(
                question=query, answer=completion, context=context_text, triplets=triplets
            )

        if session_save:
            await save_conversation_history(
                query=query,
                context_summary=context_summary,
                answer=completion,
                session_id=session_id,
            )

        return [completion]
