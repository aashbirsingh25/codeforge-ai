import uuid
import logging
import asyncio
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Memory
from app.memory.schemas import MemoryEntry, MemoryStatistics, MemorySearchResult
from app.memory.exceptions import MemoryPersistenceException, MemoryNotFoundException
from app.memory.embeddings import generate_embedding

logger = logging.getLogger("app.memory.store")


class MemoryStore:
    """
    PostgreSQL & pgvector backed memory storage for persistent user memories and vector embeddings.
    """
    def __init__(self, db: AsyncSession, user_id: Union[uuid.UUID, str]):
        self.db = db
        if isinstance(user_id, str):
            self.user_id = uuid.UUID(user_id)
        else:
            self.user_id = user_id

    async def save(self, entry: MemoryEntry) -> MemoryEntry:
        try:
            # Generate 768-dim vector embedding off the main event loop thread
            combined_text = f"{entry.title} {entry.content}"
            embedding_vector = await asyncio.to_thread(generate_embedding, combined_text)

            try:
                entry_uuid = uuid.UUID(entry.id)
            except ValueError:
                entry_uuid = uuid.uuid4()
                entry.id = str(entry_uuid)

            # Check if entry already exists
            stmt = select(Memory).where(Memory.id == entry_uuid, Memory.user_id == self.user_id)
            result = await self.db.execute(stmt)
            existing_mem = result.scalars().first()

            if existing_mem:
                existing_mem.category = entry.category
                existing_mem.title = entry.title
                existing_mem.content = entry.content
                existing_mem.metadata_json = entry.metadata
                existing_mem.tags = entry.tags
                existing_mem.timestamp = entry.timestamp
                if embedding_vector is not None:
                    existing_mem.embedding = embedding_vector
            else:
                mem = Memory(
                    id=entry_uuid,
                    user_id=self.user_id,
                    category=entry.category,
                    title=entry.title,
                    content=entry.content,
                    metadata_json=entry.metadata,
                    tags=entry.tags,
                    timestamp=entry.timestamp,
                    embedding=embedding_vector
                )
                self.db.add(mem)

            await self.db.commit()
            return entry
        except Exception as e:
            await self.db.rollback()
            raise MemoryPersistenceException(f"Failed to save memory entry {entry.id}: {str(e)}") from e

    async def load(self, entry_id: str) -> Optional[MemoryEntry]:
        try:
            try:
                entry_uuid = uuid.UUID(entry_id)
            except ValueError:
                return None

            stmt = select(Memory).where(Memory.id == entry_uuid, Memory.user_id == self.user_id)
            result = await self.db.execute(stmt)
            mem = result.scalars().first()
            if not mem:
                return None

            return MemoryEntry(
                id=str(mem.id),
                timestamp=mem.timestamp,
                category=mem.category,
                title=mem.title,
                content=mem.content,
                metadata=mem.metadata_json or {},
                tags=mem.tags or []
            )
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to load memory entry {entry_id}: {str(e)}") from e

    async def delete(self, entry_id: str) -> bool:
        try:
            try:
                entry_uuid = uuid.UUID(entry_id)
            except ValueError:
                return False

            stmt = delete(Memory).where(Memory.id == entry_uuid, Memory.user_id == self.user_id)
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except Exception as e:
            await self.db.rollback()
            raise MemoryPersistenceException(f"Failed to delete memory entry {entry_id}: {str(e)}") from e

    async def clear(self) -> None:
        try:
            stmt = delete(Memory).where(Memory.user_id == self.user_id)
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise MemoryPersistenceException(f"Failed to clear memory entries: {str(e)}") from e

    async def list(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[MemoryEntry]:
        try:
            stmt = select(Memory).where(Memory.user_id == self.user_id)

            if category:
                stmt = stmt.where(func.lower(Memory.category) == category.lower())

            stmt = stmt.order_by(Memory.timestamp.desc())

            result = await self.db.execute(stmt)
            rows = result.scalars().all()

            entries = []
            for mem in rows:
                entry_tags = mem.tags or []
                if tags:
                    entry_tags_lower = {t.lower() for t in entry_tags}
                    if not all(t.lower() in entry_tags_lower for t in tags):
                        continue

                entries.append(MemoryEntry(
                    id=str(mem.id),
                    timestamp=mem.timestamp,
                    category=mem.category,
                    title=mem.title,
                    content=mem.content,
                    metadata=mem.metadata_json or {},
                    tags=entry_tags
                ))

            if limit is not None:
                entries = entries[:limit]

            return entries
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to list memory entries: {str(e)}") from e

    async def statistics(self) -> MemoryStatistics:
        try:
            entries = await self.list()

            category_counts: Dict[str, int] = {}
            tag_counts: Dict[str, int] = {}
            storage_size_bytes = 0
            last_updated = None

            for entry in entries:
                category_counts[entry.category] = category_counts.get(entry.category, 0) + 1
                for tag in entry.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                if last_updated is None or entry.timestamp > last_updated:
                    last_updated = entry.timestamp
                storage_size_bytes += len(entry.title.encode("utf-8")) + len(entry.content.encode("utf-8"))

            return MemoryStatistics(
                total_entries=len(entries),
                category_counts=category_counts,
                tag_counts=tag_counts,
                storage_size_bytes=storage_size_bytes,
                last_updated=last_updated
            )
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to calculate memory statistics: {str(e)}") from e

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[MemorySearchResult]:
        try:
            if not query or not query.strip():
                entries = await self.list(category=category, tags=tags, limit=limit)
                return [MemorySearchResult(entry=e, score=1.0) for e in entries]

            # Generate query embedding off the main event loop thread
            query_vector = await asyncio.to_thread(generate_embedding, query)

            # 1. Primary Vector Search if query embedding succeeded
            if query_vector is not None:
                try:
                    stmt = select(
                        Memory,
                        Memory.embedding.cosine_distance(query_vector).label("distance")
                    ).where(
                        Memory.user_id == self.user_id,
                        Memory.embedding.is_not(None)
                    )

                    if category:
                        stmt = stmt.where(func.lower(Memory.category) == category.lower())

                    stmt = stmt.order_by("distance", Memory.timestamp.desc())

                    result = await self.db.execute(stmt)
                    rows = result.all()

                    results = []
                    for mem, distance in rows:
                        entry_tags = mem.tags or []
                        if tags:
                            entry_tags_lower = {t.lower() for t in entry_tags}
                            if not all(t.lower() in entry_tags_lower for t in tags):
                                continue

                        score = max(0.0, 1.0 - float(distance)) if distance is not None else 0.0
                        entry = MemoryEntry(
                            id=str(mem.id),
                            timestamp=mem.timestamp,
                            category=mem.category,
                            title=mem.title,
                            content=mem.content,
                            metadata=mem.metadata_json or {},
                            tags=entry_tags
                        )
                        results.append(MemorySearchResult(entry=entry, score=score))
                        if len(results) >= limit:
                            break

                    if results:
                        return results
                except Exception as ex:
                    logger.warning(f"Vector search failed, falling back to keyword search: {ex}")

            # 2. Fallback Keyword Search if embedding generation or vector query failed/returned no results
            entries = await self.list(category=category, tags=tags)
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
                    tf = 0.0
                    if token in title_text:
                        tf += 3.0
                    if token in content_text:
                        tf += content_text.count(token) * 1.0
                    for t in tags_lower:
                        if token in t:
                            tf += 2.0
                    if tf > 0:
                        score += tf

                if score > 0:
                    scored_results.append((entry, score))

            scored_results.sort(key=lambda x: (x[1], x[0].timestamp), reverse=True)
            return [MemorySearchResult(entry=entry, score=score) for entry, score in scored_results[:limit]]
        except Exception as e:
            raise MemoryPersistenceException(f"Failed to search memory entries: {str(e)}") from e
