<<<<<<< HEAD
from base import GlobalState
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph.message import add_messages
=======
from state.base import GlobalState
from typing import Annotated, List
>>>>>>> main

# 기존 GlobalState를 상속받습니다.
class InternalState(GlobalState):
    # 분석 노드에서 추출할 구체적인 작업 리스트
    target_sections: Annotated[List[str], 'Sections to be updated']
    # 이전 질문 내용
    required_data_points: Annotated[List[str], 'Specific points to fill']
    # Analyzer가 판단한 유저의 의도 (내부 로직 분기용)
    internal_user_intent: Annotated[str, 'Internal decision flag']