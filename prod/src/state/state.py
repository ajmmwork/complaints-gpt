from typing import TypedDict, List, Any, Literal, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class DateRange(TypedDict):
    start_date: str
    end_date: str


class Filters(TypedDict):
    requested_company: str
    company: str
    company_validation_flag: str
    issue: Optional[str]
    product: Optional[str]
    state: Optional[str]
    date_received: List[DateRange]
    executed_fallbacks: int


class IngestionJob(TypedDict):
    company: str
    start_date: str
    end_date: str
    status: Literal["pending", "running", "failed", "complete"]
    error_message: Optional[str]
    approval: str


class CompanyResolution(TypedDict):
    status: Literal["pending", "running", "failed", "complete"]
    error_message: Optional[str]


class CompanyReview(TypedDict):
    status: Literal["pending", "running", "failed", "complete"]
    error_message: Optional[str]


class QueryTask(TypedDict):
    task_id: str
    query: str
    sql: Optional[str]
    desc: str
    params: dict[str, Any]
    query_type: Literal["statistical", "semantic"]
    filters: List[Filters]
    data: dict[str, Any]
    error_message: Optional[str]
    status: Literal["pending", "running", "failed", "complete"]


class State(TypedDict, total=False):
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    filters: List[Filters]
    company_review: CompanyReview
    company_resolution: CompanyResolution
    ingestion_jobs: List[IngestionJob]
    status: Literal["pending", "running", "failed", "complete"]
    error_message: Optional[str]
    answer: str
    query_tasks: List[QueryTask]
    partial_semantic_answer: Optional[str]
    partial_statistical_answer: Optional[str]
    interrupt_id: int