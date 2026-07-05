from fastapi import APIRouter

router = APIRouter()

@router.get("")
def get_memory_summary():
    """
    Get summary of agent memory stores (short-term state & long-term vector store entries).
    """
    return {
        "short_term_contexts_count": 0,
        "long_term_vector_nodes": 0,
        "status": "ready"
    }
