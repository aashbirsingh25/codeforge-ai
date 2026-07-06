import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.core.config import settings
from app.memory.schemas import MemoryEntry, MemoryStatistics, MemorySearchResult
from app.memory.exceptions import MemoryPersistenceException, MemoryNotFoundException

logger = logging.getLogger("app.memory.store")

class MemoryStore:
    def __init__(self, memory_dir: Optional[Path] = None):
        if memory_dir is None:
            self.memory_dir = settings.WORKSPACE_DIR / ".memory"
        else:
            self.memory_dir = memory_dir
        
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to create memory directory: {str(e)}")

    def save(self, entry: MemoryEntry) -> None:
        try:
            file_path = self.memory_dir / f"{entry.id}.json"
            data = json.loads(entry.model_dump_json())
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to save memory entry {entry.id}: {str(e)}")

    def load(self, entry_id: str) -> Optional[MemoryEntry]:
        file_path = self.memory_dir / f"{entry_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return MemoryEntry(**data)
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to load memory entry {entry_id}: {str(e)}")

    def delete(self, entry_id: str) -> bool:
        file_path = self.memory_dir / f"{entry_id}.json"
        if not file_path.exists():
            return False
        try:
            file_path.unlink()
            return True
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to delete memory entry {entry_id}: {str(e)}")

    def clear(self) -> None:
        try:
            for item in self.memory_dir.glob("*.json"):
                item.unlink()
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to clear memory directory: {str(e)}")

    def list(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[MemoryEntry]:
        entries = []
        try:
            for file_path in self.memory_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    entry = MemoryEntry(**data)
                    
                    # Apply category filter
                    if category and entry.category.lower() != category.lower():
                        continue
                    
                    # Apply tags filter (must match all tags if specified)
                    if tags:
                        entry_tags_lower = {t.lower() for t in entry.tags}
                        if not all(t.lower() in entry_tags_lower for t in tags):
                            continue
                            
                    entries.append(entry)
                except Exception as ex:
                    logger.warning(f"Skipping corrupted memory file {file_path.name}: {ex}")
            
            # Sort by timestamp descending (newest first)
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            
            if limit is not None:
                entries = entries[:limit]
                
            return entries
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to list memory entries: {str(e)}")

    def statistics(self) -> MemoryStatistics:
        try:
            entries = self.list()
            
            category_counts = {}
            tag_counts = {}
            storage_size_bytes = 0
            last_updated = None
            
            for file_path in self.memory_dir.glob("*.json"):
                try:
                    storage_size_bytes += file_path.stat().st_size
                except Exception:
                    pass
                    
            for entry in entries:
                category_counts[entry.category] = category_counts.get(entry.category, 0) + 1
                for tag in entry.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                if last_updated is None or entry.timestamp > last_updated:
                    last_updated = entry.timestamp
                    
            return MemoryStatistics(
                total_entries=len(entries),
                category_counts=category_counts,
                tag_counts=tag_counts,
                storage_size_bytes=storage_size_bytes,
                last_updated=last_updated
            )
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to calculate memory statistics: {str(e)}")

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[MemorySearchResult]:
        try:
            entries = self.list(category=category, tags=tags)
            if not query:
                return [MemorySearchResult(entry=e, score=1.0) for e in entries[:limit]]

            # Split query into words
            query_tokens = [t.lower() for t in query.split() if t]
            if not query_tokens:
                return [MemorySearchResult(entry=e, score=1.0) for e in entries[:limit]]

            scored_results = []
            for entry in entries:
                score = 0.0
                
                title_text = entry.title.lower()
                content_text = entry.content.lower()
                tags_lower = [t.lower() for t in entry.tags]
                
                for token in query_tokens:
                    tf = 0
                    if token in title_text:
                        tf += 3.0  # title match boost
                    if token in content_text:
                        tf += content_text.count(token) * 1.0
                    for t in tags_lower:
                        if token in t:
                            tf += 2.0  # tag match boost
                    
                    if tf > 0:
                        score += tf
                
                if score > 0:
                    scored_results.append((entry, score))
            
            # Sort by score descending, then by timestamp descending
            scored_results.sort(key=lambda x: (x[1], x[0].timestamp), reverse=True)
            
            # Format response
            results = [MemorySearchResult(entry=entry, score=score) for entry, score in scored_results[:limit]]
            return results
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to search memory entries: {str(e)}")
