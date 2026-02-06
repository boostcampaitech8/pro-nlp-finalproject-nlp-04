# Sample Plan 14

> A Technical plan regarding 데이터 무결성과 투명성 보장

*생성 방법: blueprint*

---

## 목차

- [1. 1. 스마트 컨트랙트 설계](#1-1.-스마트-컨트랙트-설계)
- [2. 2. 프라이빗 체인 구성](#2-2.-프라이빗-체인-구성)
- [3. 3. QR 코드 연동](#3-3.-qr-코드-연동)

---

## 1. 1. 스마트 컨트랙트 설계

#### **1.1 핵심 엔티티 정의**  
- **상태(State) Enum**:  
  ```solidity
  enum Status { RECEIVED, INSPECTED, PROCESSING, QUALITY_CHECK, PACKAGED, SHIPPED, DELIVERED }
  ```
- **배치(Batch) Struct**:  
  ```solidity
  struct Batch {
      uint256 batchId;
      uint256 timestamp;
      Status currentStatus;
      StatusHistory[] statusHistory;
      address responsibleParty;
  }
  ```
- **상태 이력(StatusHistory) Struct**:  
  ```solidity
  struct StatusHistory {
      Status oldStatus;
      Status newStatus;
      uint256 timestamp;
      address updatedBy; // 트리거 주체 (검수자, 제조팀 등)
  }
  ```

#### **1.2 데이터 저장소**  
- **배치 매핑**:  
  ```solidity
  mapping(uint256 => Batch) public batches;
  ```
- **역할 기반 접근 제어**:  
  OpenZeppelin의 `AccessControl` 모듈 활용 (예: `SUPPLIER_ROLE`, `INSPECTOR_ROLE`, `MANUFACTURER_ROLE` 등).

#### **1.3 상태 전이 로직**  
- **조건 기반 트리거 함수**:  
  ```solidity
  function updateStatus(uint256 _batchId, Status _newStatus) external {
      Batch storage batch = batches[_batchId];
      require(validTransition(batch.currentStatus, _newStatus), "Invalid status transition");
      require(hasRole(getRole(_newStatus), msg.sender), "Unauthorized role");
      
      batch.statusHistory.push(StatusHistory({
          oldStatus: batch.currentStatus,
          newStatus: _newStatus,
          timestamp: block.timestamp,
          updatedBy: msg.sender
      }));
      batch.currentStatus = _newStatus;
      emit StatusUpdated(_batchId, _newStatus, msg.sender);
  }
  ```
- **유효성 검증 함수**:  
  ```solidity
  function validTransition(Status _from, Status _to) internal pure returns (bool) {
      // 전이 규칙 정의 (예: RECEIVED → INSPECTED 만 허용)
      if (_from == Status.RECEIVED && _to == Status.INSPECTED) return true;
      if (_from == Status.INSPECTED && _to == Status.PROCESSING) return true;
      // ... 기타 전이 규칙
      return false;
  }
  ```

#### **1.4 이벤트 및 감사 추적**  
- **상태 변경 이벤트**:  
  ```solidity
  event StatusUpdated(uint256 indexed batchId, Status newStatus, address updatedBy);
  ```
- **이력 조회 함수**:  
  ```solidity
  function getStatusHistory(uint256 _batchId) external view returns (StatusHistory[] memory) {
      return batches[_batchId].statusHistory;
  }
  ```

#### **1.5 보안 및 확장성**  
- **불변 데이터 보장**:  
  상태 이력 배열은 `append-only`로 설계되어 과거 기록 수정 불가.  
- **멀티체인 연동 준비**:  
  이벤트 로그를 타 체인과 동기화하기 위한 `CrossChainReference` 필드 추가 가능.  
- **QR 코드 연동 포인트**:  
  `batchId`는 QR 코드 생성 시 사용되며, 스캔 시 `updateStatus` 함수 호출로 연결됨.  

#### **1.6 예외 처리**  
- **중복 상태 전이 방지**:  
  ```solidity
  require(batch.currentStatus != _newStatus, "Duplicate status");
  ```
- **타임스탬프 검증**:  
  상태 변경 시 최소 시간 간격(예: 1시간) 강제하여 실수 방지.
