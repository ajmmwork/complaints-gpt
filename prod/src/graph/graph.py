from langgraph.graph import StateGraph, START, END
from src.state.state import State

from src.nodes.MessageInput import MessageInput
from src.nodes.FilterExtraction import FilterExtraction
from src.nodes.FilterExtractionRouter import FilterExtractionRouter

from src.nodes.CompanyValidation import CompanyValidation
from src.nodes.FilterValidation import FilterValidation
from src.nodes.CompanyValidationFallbackRouter import CompanyValidationFallbackRouter
from src.nodes.CompanyValidationFallback import CompanyValidationFallback

from src.nodes.JobCreation import JobCreation
from src.nodes.JobConsolidation import JobConsolidation
from src.nodes.DataCoverageControl import DataCoverage
from src.nodes.ExecutionRequirementRouter import ExecutionRequirementRouter
from src.nodes.Ingestion import Ingestion

from src.nodes.QueryDecomposition import QueryDecomposition
from src.nodes.SQLQueryDevelopment import SQLQueryDevelopment
from src.nodes.SQLQueryValidation import SQLQueryValidation
from src.nodes.SQLQueryValidationRouter import SQLQueryValidationRouter
from src.nodes.SQLSubTaskExecution import SQLSubTaskExecution

from src.nodes.TaskExecutionRouter import TaskExecutionRouter
from src.nodes.SemanticEnrichment import SemanticEnrichment
from src.nodes.RAGSubTaskExecution import RAGSubTaskExecution

from src.nodes.PartialAnswer import PartialSemanticAnswer, PartialStatisticalAnswer
from src.nodes.AppendAIMessage import AppendAIMessage
from src.nodes.Synthetsis import Synthesis

from src.db.DatabaseManager import DatabaseManager

import logging
import os
import yaml
import psycopg


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s"
)


def load_queries():
    with open("src/db/queries.yaml", "r") as file:
        return yaml.safe_load(file)



def get_agent_connection():
    return psycopg.connect(
        dbname=os.environ.get("dbname"),
        user=os.environ.get("agent_user"),
        password=os.environ.get("agent_password"),
        host=os.environ.get("host"),
        port=os.environ.get("port"),
    )


def build_database_manager() -> DatabaseManager:
    queries = load_queries()


    # Runtime graph uses restricted agent role.
    agent_conn = get_agent_connection()

    return DatabaseManager(
        connection=agent_conn,
        queries=queries,
        verbose=True,
        run_setup=False,
    )


mgr = build_database_manager()


def build_graph():
    builder = StateGraph(State)

    builder.add_node("MessageInput", MessageInput)
    builder.add_node("FilterExtraction", FilterExtraction)

    builder.add_node(
        "CompanyValidation",
        lambda state: CompanyValidation(state, mgr)
    )

    builder.add_node(
        "FilterValidation",
        lambda state: FilterValidation(state, mgr)
    )

    builder.add_node(
        "CompanyValidationFallback",
        lambda state: CompanyValidationFallback(state, mgr)
    )

    builder.add_node("JobCreation", JobCreation)
    builder.add_node("JobConsolidation", JobConsolidation)

    builder.add_node(
        "DataCoverage",
        lambda state: DataCoverage(state, mgr)
    )

    builder.add_node(
        "Ingestion",
        lambda state: Ingestion(state, mgr)
    )

    builder.add_node("QueryDecomposition", QueryDecomposition)
    builder.add_node("SQLQueryDevelopment", SQLQueryDevelopment)
    builder.add_node("SQLQueryValidation", SQLQueryValidation)

    builder.add_node(
        "SQLSubTaskExecution",
        lambda state: SQLSubTaskExecution(state, mgr)
    )

    builder.add_node("TaskExecutionRouterNode", lambda state: {})
    builder.add_node("SemanticEnrichment", SemanticEnrichment)

    builder.add_node(
        "RAGSubTaskExecution",
        lambda state: RAGSubTaskExecution(state, mgr)
    )

    builder.add_node("PartialStatisticalAnswer", PartialStatisticalAnswer)
    builder.add_node("PartialSemanticAnswer", PartialSemanticAnswer)
    builder.add_node("Synthesis", Synthesis)
    builder.add_node("AppendAIMessage", AppendAIMessage)

    builder.add_edge(START, "MessageInput")
    builder.add_edge("MessageInput", "FilterExtraction")

    builder.add_conditional_edges(
        "FilterExtraction",
        FilterExtractionRouter,
        {
            "Failed Query": "AppendAIMessage",
            "Valid Query": "CompanyValidation",
        }
    )

    builder.add_conditional_edges(
        "CompanyValidation",
        CompanyValidationFallbackRouter,
        {
            "Company Validation Failed": "CompanyValidationFallback",
            "Ready for Review": "FilterValidation",
        }
    )

    builder.add_edge("CompanyValidationFallback", "CompanyValidation")
    builder.add_edge("FilterValidation", "JobCreation")
    builder.add_edge("JobCreation", "DataCoverage")

    builder.add_conditional_edges(
        "DataCoverage",
        ExecutionRequirementRouter,
        {
            "Needs Ingestion": "JobConsolidation",
            "Does Not Need Ingestion": "QueryDecomposition",
        }
    )

    builder.add_edge("JobConsolidation", "Ingestion")
    builder.add_edge("Ingestion", "QueryDecomposition")

    builder.add_edge("QueryDecomposition", "SQLQueryDevelopment")
    builder.add_edge("SQLQueryDevelopment", "SQLQueryValidation")

    builder.add_conditional_edges(
        "SQLQueryValidation",
        SQLQueryValidationRouter,
        {
            "Invalid SQL script(s)": "SQLQueryDevelopment",
            "Validated SQL scripts": "TaskExecutionRouterNode",
        }
    )

    builder.add_conditional_edges(
        "TaskExecutionRouterNode",
        TaskExecutionRouter,
        {
            "Statistical Subtasks Pending Execution": "SQLSubTaskExecution",
            "Semantic Subtasks Pending Execution": "SemanticEnrichment",
            "No Subtasks Pending Execution": "Synthesis",
        }
    )

    builder.add_edge("SQLSubTaskExecution", "PartialStatisticalAnswer")
    builder.add_edge("PartialStatisticalAnswer", "TaskExecutionRouterNode")

    builder.add_edge("SemanticEnrichment", "RAGSubTaskExecution")
    builder.add_edge("RAGSubTaskExecution", "PartialSemanticAnswer")
    builder.add_edge("PartialSemanticAnswer", "TaskExecutionRouterNode")

    builder.add_edge("Synthesis", "AppendAIMessage")
    builder.add_edge("AppendAIMessage", END)

    return builder.compile()


graph = build_graph()