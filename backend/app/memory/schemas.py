from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MemoryEntry(BaseModel):
    id: str = Field(..., description="Unique memory entry identifier")
    timestamp: datetime = Field(..., description="Timestamp of the memory creation")
    category: str = Field(..., description="Category of the memory (e.g., execution, plan, tool_output, observation, conversation)")
    title: str = Field(..., description="Short title describing the memory")
    content: str = Field(..., description="The main content of the memory")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")
    tags: List[str] = Field(default_factory=list, description="Tags associated with the memory")

class MemorySummary(BaseModel):
    total_entries: int = Field(..., description="Total number of memory entries")
    category_counts: Dict[str, int] = Field(..., description="Count of entries per category")
    recent_entries: List[MemoryEntry] = Field(..., description="List of most recent memory entries")
    short_term_contexts_count: int = Field(0, description="Backward compatibility field for short term count")
    long_term_vector_nodes: int = Field(0, description="Backward compatibility field for long term vector nodes")
    status: str = Field("ready", description="Backward compatibility field for status")

class MemorySearchRequest(BaseModel):
    query: str = Field(..., description="Search query string")
    category: Optional[str] = Field(None, description="Filter by category")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: Optional[int] = Field(10, description="Maximum number of search results to return")

class MemorySearchResult(BaseModel):
    entry: MemoryEntry = Field(..., description="The matched memory entry")
    score: float = Field(..., description="Rank/similarity score")

class MemorySearchResponse(BaseModel):
    results: List[MemorySearchResult] = Field(..., description="Ranked list of memory search results")

class ConversationMemory(MemoryEntry):
    pass

class ExecutionMemory(MemoryEntry):
    pass

class ObservationMemory(MemoryEntry):
    pass

class ToolMemory(MemoryEntry):
    pass

class MemoryStatistics(BaseModel):
    total_entries: int = Field(..., description="Total count of entries")
    category_counts: Dict[str, int] = Field(..., description="Count of entries per category")
    tag_counts: Dict[str, int] = Field(..., description="Frequency of each tag")
    storage_size_bytes: int = Field(..., description="Approximate size of the storage in bytes")
    last_updated: Optional[datetime] = Field(None, description="Timestamp of the latest update")
