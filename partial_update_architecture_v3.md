# 부분 문서 수정을 위한 에이전트 아키텍처 제안 (v3: Final)

유저의 심층 피드백을 반영하여, **현실적인 리팩토링 비용**과 **장기적인 유지보수성** 사이의 균형을 맞춘 최종 안입니다.

## 1. 쟁점 분석 및 해결 방안

### A. State 구조: `List[String]` vs `List[Dict]`
> **Q:** "GlobalState를 `List[Dict]`로 바꾸면 대공사가 일어나지 않나? 메타데이터 관리의 효율적인 방법은?"

**분석 (Analysis):**
*   **현재 상황**: `PlanInternalState`(내부)는 이미 `List[Dict]`를 사용 중일 가능성이 높으나, `GlobalState`(외부)는 `List[str]`로 정의되어 있어 정보(ID, 시각화 매핑) 손실이 발생합니다.
*   **Trade-off**:
    *   `List[str]` 유지: 다른 모듈 수정 불필요(장점). 하지만 에디터 기능(특정 위치 수정, 시각화 매핑) 구현 시 "몇 번째 문단인지" 매번 파싱해야 함(치명적 비효율).
    *   `List[Dict]` 변경: 초기 리팩토링 비용 발생(단점). 하지만 에디터 앱의 필수 데이터 구조(ID 기반 관리) 확보.

**제안 (Recommendation): "점진적 마이그레이션 (Dual Property Strategy)"**
당장의 `List[str]` 의존성을 끊기 어렵다면, State에 두 필드를 병행합니다.
*   `sections_text: List[str]` (Legacy/Display용, Computed Property처럼 동작)
*   **`sections_data: List[SectionModel]` (Core Logic용, 실제 Source of Truth)**
    *   *나중에 `sections_text`는 `[s['content'] for s in sections_data]` 형태로 동적 생성하여 반환.*

### B. State 세분화 (Granularity)
> **Q:** "PlanInternal, Vis, Gen, Edit State로 나누는 게 좋을까?"

**제안:** **적극 찬성 (Separation of Concerns)**
각 파이프라인이 전용 State를 가지면, 불필요한 데이터가 컨텍스트에 섞이는 것을 방지할 수 있습니다.

```python
# 계층 구조 (Hierarchy)
GlobalState
└── PlanState (Shared Output)
    ├── CreationState (For Generation Loop)
    ├── EditingState (For User Interaction)
    └── VisualState (For Chart Gen)
```

### C. 콘텐츠 관리 단위: 문장 vs 섹션
> **Q:** "문장 단위로 관리? 비즈니스 톤 매너 유지는?"

**제안:** **"섹션(Section) 단위 관리 & 마크다운 네이티브"**
*   **이유**: LLM은 문장 단위로 쪼개서 생성하면 문맥(Flow)이 끊겨 "로봇 같은 글"이 나옵니다. 비즈니스 톤앤매너는 문단 간의 호흡에서 나옵니다.
*   **전략**:
    *   데이터 저장: **섹션 단위 (`Dict`)**
    *   수정 처리: 유저가 "이 문장 고쳐줘"라고 해도, 에이전트는 **"해당 문장이 포함된 문단/섹션 전체"를 재작성(Rewrite)** 하여 덮어씌웁니다.
    *   이 방식이 문맥 자연스러움과 데이터 관리 단순함(ID 갯수 적음)의 최적점입니다.

### D. 모듈 이름: Pipeline vs Graph
**제안:** **`graphs` (또는 `workflows`)**
*   LangGraph를 사용하므로 `graphs`가 가장 직관적입니다. (`pipeline`은 선형적인 느낌이 강함)
*   `src/agents/plan/graphs/creation.py`, `src/agents/plan/graphs/editing.py`

---

## 2. 최종 아키텍처 청사진

### 디렉토리 구조 (Directory Structure)
```text
src/
└── agents/
    └── plan/
        ├── states/             # [NEW] State 정의 분리
        │   ├── base.py         # PlanState (Shared)
        │   ├── creation.py     # Section Generation Loop용
        │   └── editing.py      # User Modification용
        ├── graphs/             # [Renamed from pipeline]
        │   ├── main.py         # Router (Creation vs Edit)
        │   ├── creation.py     # 생성 루프
        │   └── editing.py      # 편집 워크플로우
        └── components/         # [Renamed from nodes] 순수 로직/함수
            ├── generator.py
            ├── editor.py       # (Refiner, Rewriter)
            └── visual.py
```

### 데이터 구조 (State Definitions)

```python
# src/agents/plan/states/base.py
class SectionModel(TypedDict):
    id: str             # UUID
    type: str           # "text", "visual", "container"
    content: str        # Markdown Text
    metadata: Dict      # { "visual_ref": "chart_1", "source": "search_2" }

class PlanState(TypedDict):
    # Core Data
    sections: List[SectionModel]  # Source of Truth
    
    # Legacy Support (Optional)
    # sections_text: List[str] 
    
    blueprint: List[Dict]

# src/agents/plan/states/editing.py
class EditingState(PlanState):
    request: str            # 유저 요청 ("이거 고쳐줘")
    target_id: str          # 식별된 섹션 ID
    diff_data: Dict         # { "before": ..., "after": ... }
```

## 3. 구현 로드맵 (Action Plan)

### Phase 1: 기반 마련 (Refactoring)
1.  **State 분리**: `src/state/plan.py`를 `src/agents/plan/states/` 패키지로 이동 및 세분화.
2.  **`List[Dict]` 도입**: `GlobalState`는 건드리지 않더라도, `PlanInternalState`(Creation용)는 확실하게 `SectionModel` 리스트를 쓰도록 정리.

### Phase 2: 편집 그래프 (Editing Graph) 구현
1.  **Router Node**: 유저 메시지가 들어오면 `Creation`으로 갈지 `Editing`으로 갈지 결정하는 루트 노드 구현.
2.  **Editor Agent**: "섹션 전체 + 수정 지시사항"을 입력받아 "수정된 섹션"을 뱉는 프롬프트 개발.
3.  **App 연동**: 프론트엔드에서 "수정할 섹션 ID"를 넘겨줄 수 없다면, **"현재 보고 있는 섹션"** 혹은 **"자연어 검색"**을 통해 타겟을 찾는 `Finder Node` 추가.

## 4. 유저 질문에 대한 답변 요약

1.  **GlobalState 변경 부담?**: 부담스럽다면 내부 State만이라도 고도화하세요. 단, 장기적으로 에디터 앱을 만들 거라면 `List[Dict]`로의 전환은 **피할 수 없는 기술 부채** 해결 과정입니다.
2.  **State 세분화?**: **강력 추천**. 디버깅과 유지보수가 훨씬 쉬워집니다.
3.  **문장 관리?**: **반대**. 섹션/문단 단위를 유지해야 LLM의 작문 품질(Tone & Manner)이 유지됩니다.
4.  **Edit Trigger**: Editing Graph는 **"Reactive"** 합니다. 유저의 `input` 신호가 있을 때만 깨어나는 별도의 진입점(`entry_point`)을 가질 수 있습니다.
