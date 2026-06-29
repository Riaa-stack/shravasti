from sqlalchemy import Column, String, Integer, ForeignKey, JSON, UniqueConstraint
from app.db.base import Base

class GraphNode(Base):
    __tablename__ = "graph_nodes"

    id = Column(String, primary_key=True, index=True)
    label = Column(String, index=True)
    properties = Column(JSON, default={})

class GraphEdge(Base):
    __tablename__ = "graph_edges"
    __table_args__ = (UniqueConstraint('source_id', 'target_id', 'type', name='uq_graph_edge'),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_id = Column(String, ForeignKey("graph_nodes.id", ondelete="CASCADE"), index=True)
    target_id = Column(String, ForeignKey("graph_nodes.id", ondelete="CASCADE"), index=True)
    type = Column(String, index=True)
