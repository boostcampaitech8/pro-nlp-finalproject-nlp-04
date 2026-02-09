# Vibe Planner: AI-Powered Planning Assistant

## 1. System Overview
Vibe Planner는 사용자의 아이디어를 구체적인 기획서로 변환해주는 AI 에이전트 시스템입니다. Supervisor 에이전트를 중심으로 Idea, Plan, Research, Visual 에이전트가 유기적으로 협력하여 문서를 작성합니다.

---

## 2. Supervisor Graph (Central Control)
Supervisor는 사용자의 입력을 분석하고 적절한 하위 에이전트로 작업을 라우팅하는 중앙 제어 장치입니다.

```mermaid
graph TD
    start((Start)) --> supervisor
    
    supervisor[Supervisor Node]
    router{Router Logic}
    
    supervisor --> router
    
    router -->|ASK_USER| ask_user[Ask User]
    router -->|RUN_IDEA_STRUCTURING| prepare_idea[Prepare Idea Structuring]
    router -->|RUN_PLANNING| plan_phase[Plan Phase]
    router -->|RUN_RESEARCH| research_phase[Research Phase]
    
    ask_user --> user_input((End/User Input))
    
    prepare_idea --> idea_graph[[Idea Subgraph]]
    idea_graph --> supervisor
    
    plan_phase[[Plan Subgraph]] --> supervisor
    
    research_phase[[Research Subgraph]] --> supervisor
    
    style supervisor fill:#f9f,stroke:#333,stroke-width:4px
    style router fill:#fff,stroke:#333,stroke-dasharray: 5 5
```

---

## 3. Overall State Transition Diagram
전체 시스템의 상태 전이와 에이전트 간의 상호작용 흐름도입니다.

```mermaid
graph TD
    %% Nodes
    subgraph Supervisor_Layer [Supervisor Layer]
        S_Node[Supervisor Node]
        S_Router{Router}
        S_Ask[Ask User]
    end

    subgraph Idea_Agent [Idea Agent]
        I_Analyzer[Analyzer]
        I_Creator[Creator]
        I_Updater[Updater]
        I_Questioner[Questioner]
        I_Evaluator[Evaluator]
    end

    subgraph Plan_Agent [Plan Agent]
        P_Init[Initialize]
        P_Gen[Generate Section]
        P_Check{Research Check}
        P_Visual[Process Visual]
        P_Save[Save & Next]
    end

    subgraph Research_Agent [Research Agent]
        R_Query[Query Gen]
        R_Search[Search]
        R_Analysis[Analysis]
    end

    %% Supervisor Flow
    Start((Start)) --> S_Node
    S_Node --> S_Router
    S_Router -->|ASK_USER| S_Ask
    S_Router -->|RUN_IDEA_STRUCTURING| I_Analyzer
    S_Router -->|RUN_PLANNING| P_Init
    S_Router -->|RUN_RESEARCH| R_Query

    %% Idea Flow
    I_Analyzer --> I_Creator
    I_Analyzer --> I_Updater
    I_Analyzer --> I_Questioner
    I_Creator --> I_Questioner
    I_Updater --> I_Questioner
    I_Questioner --> I_Evaluator
    I_Evaluator -->|REJECTED| I_Analyzer
    I_Evaluator -->|COMPLETE / WAIT_FOR_USER| S_Node

    %% Plan Flow
    P_Init --> P_Gen
    P_Gen --> P_Check
    P_Check -->|Needs Research| S_Node
    P_Check -->|No Research| P_Visual
    P_Visual --> P_Save
    P_Save -->|Section Complete| S_Node

    %% Research Flow
    R_Query --> R_Search
    R_Search --> R_Analysis
    R_Analysis --> S_Node
    R_Search -->|No Analysis| S_Node

    S_Ask --> End((End/Wait))
    
    %% Styling
    style S_Node fill:#f9f,stroke:#333,stroke-width:2px
    style I_Analyzer fill:#bbf,stroke:#333
    style P_Gen fill:#bfb,stroke:#333
    style R_Query fill:#fbf,stroke:#333
```
