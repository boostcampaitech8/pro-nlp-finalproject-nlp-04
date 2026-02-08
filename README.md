# Vibe Planner: AI-Powered Planning Assistant

## 1. System Overview
Vibe Planner는 사용자의 아이디어를 구체적인 기획서로 변환해주는 AI 에이전트 시스템입니다. Supervisor 에이전트를 중심으로 Idea, Plan, Research, Visual 에이전트가 유기적으로 협력하여 문서를 작성합니다.

---

## 2. Supervisor Graph (Central Control)
Supervisor는 사용자의 입력을 분석하고 적절한 하위 에이전트로 작업을 라우팅하는 중앙 제어 장치입니다.

```mermaid
stateDiagram-v2
    direction TB

    [*] --> Supervisor

    state Supervisor {
        [*] --> Router
        Router --> AskUser: User Input Required
        Router --> IdeaAgent: Structuring
        Router --> PlanAgent: Planning
        Router --> ResearchAgent: Research
        
        AskUser --> [*]: Wait for Input
        
        note right of Router
            Decides next action based on
            current state and user input
        end note
    }

    state IdeaAgent {
        [*] --> Analyzer
        Analyzer --> Creator
        Analyzer --> Updater
        Analyzer --> Questioner
        
        Creator --> Questioner
        Updater --> Questioner
        Questioner --> Evaluator
        
        Evaluator --> Analyzer: REJECTED
        Evaluator --> [*]: COMPLETE
    }

    state PlanAgent {
        [*] --> Initialize
        Initialize --> GenerateSection
        GenerateSection --> CheckResearch
        
        CheckResearch --> [*]: Needs Research
        CheckResearch --> ProcessVisual: No Research
        
        ProcessVisual --> SaveAndNext
        SaveAndNext --> [*]: Section Complete
    }

    state ResearchAgent {
        [*] --> QueryGen
        QueryGen --> Search
        Search --> Analysis: Need Analysis
        Search --> [*]: Simple Search
        Analysis --> [*]
    }

    IdeaAgent --> Supervisor: Result / Status
    PlanAgent --> Supervisor: Section / Status
    ResearchAgent --> Supervisor: Information
```

---

## 3. Interaction Sequence Diagram (Plan & Research Loop)
Plan Agent와 Research Agent 간의 상호작용 및 데이터 흐름을 상세하게 표현한 시퀀스 다이어그램입니다.

```mermaid
sequenceDiagram
    participant Idea as Idea Agent
    participant Sup as Supervisor
    participant Plan as Plan Agent
    participant Res as Research Agent

    note over Sup: 사용자 입력 분석

    rect rgb(255, 240, 245)
        Sup->>Idea: 아이디어 구체화 요청
        note right of Idea: 아이디어 분석 및 구조화
        loop 아이디어 발전 과정
            Idea->>Idea: 4단계 사고 과정 (분석-생성-비판-평가)
        end
        Idea->>Sup: 구조화된 아이디어 반환
    end

    Sup->>Plan: 기획서 작성 요청

    rect rgb(240, 255, 240)
        note over Plan: 섹션 초안 작성 시도
        note over Plan: 리서치 필요성 평가

        alt 정보 부족 (리서치 필요)
            Plan->>Sup: 리서치 요청 신호 전송
            note right of Sup: 리서치 모드로 전환 감지
            
            Sup->>Res: 리서치 작업 실행
            
            rect rgb(240, 248, 255)
                note over Res: 검색어 생성 -> 웹 검색 -> 결과 분석
                loop 심층 탐색 과정
                    Res->>Res: 정보 수집 및 검증
                end
            end
            
            Res->>Sup: 검증된 근거 자료 반환
            Sup->>Plan: 기획 모드 복귀 (섹션 재작성)
            
            note over Plan: 검색 결과를 반영하여 섹션 완성
        else 정보 충분
            note over Plan: 섹션 작성 완료
        end
        
        Plan->>Sup: 완성된 섹션 전달
    end
```
