"""
파이프라인 로깅 시스템
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class PipelineLogger:
    """파이프라인 실행 로그 기록"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"pipeline_{timestamp}.log"
        self.json_file = self.log_dir / f"pipeline_{timestamp}.json"
        
        self.logs: List[Dict[str, Any]] = []
        
    def log(self, level: LogLevel, stage: str, message: str, data: Dict[str, Any] = None):
        """로그 기록"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "stage": stage,
            "message": message,
            "data": data or {}
        }
        
        self.logs.append(log_entry)
        
        # 텍스트 로그 파일에 기록
        with open(self.log_file, "a", encoding="utf-8") as f:
            log_line = f"[{log_entry['timestamp']}] [{level.value}] [{stage}] {message}\n"
            if data:
                log_line += f"  Data: {json.dumps(data, ensure_ascii=False, indent=2)}\n"
            f.write(log_line)
    
    def log_section_generation(self, section_number: str, section_title: str, method: str):
        """섹션 생성 로그"""
        self.log(
            LogLevel.INFO,
            "section_generation",
            f"섹션 생성 시작: {section_number}. {section_title}",
            {"section_number": section_number, "title": section_title, "method": method}
        )
    
    def log_visual_decision(self, section_number: str, decision: Dict[str, Any]):
        """시각화 결정 로그"""
        needs = []
        if decision.get("needs_table"):
            needs.append(f"표({decision.get('table_type')})")
        if decision.get("needs_diagram"):
            needs.append(f"다이어그램({decision.get('diagram_type')})")
        if decision.get("needs_image_search"):
            needs.append("이미지 검색")
        if decision.get("needs_image_gen"):
            needs.append("이미지 생성")
        
        message = f"시각화 결정: {', '.join(needs) if needs else '없음'}"
        
        self.log(
            LogLevel.INFO,
            "visual_decision",
            message,
            {
                "section_number": section_number,
                "decision": decision,
                "reason": decision.get("reason", "")
            }
        )
    
    def log_visual_generation(self, section_number: str, visual_type: str, success: bool, error: str = None):
        """시각화 생성 로그"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        message = f"시각화 생성 {'성공' if success else '실패'}: {visual_type}"
        
        self.log(
            level,
            "visual_generation",
            message,
            {
                "section_number": section_number,
                "visual_type": visual_type,
                "success": success,
                "error": error
            }
        )
    
    def log_validation(self, section_number: str, is_valid: bool, score: float, reason: str):
        """검증 결과 로그"""
        level = LogLevel.INFO if is_valid else LogLevel.WARNING
        message = f"검증 결과: {'적합' if is_valid else '부적합'} (점수: {score:.2f})"
        
        self.log(
            level,
            "validation",
            message,
            {
                "section_number": section_number,
                "is_valid": is_valid,
                "score": score,
                "reason": reason
            }
        )
    
    def log_pipeline_start(self, method: str, idea_summary: str):
        """파이프라인 시작 로그"""
        self.log(
            LogLevel.INFO,
            "pipeline_start",
            f"파이프라인 시작 (방법: {method})",
            {"method": method, "idea": idea_summary[:100]}
        )
    
    def log_pipeline_end(self, sections_count: int, visuals_count: int, output_path: str):
        """파이프라인 종료 로그"""
        self.log(
            LogLevel.INFO,
            "pipeline_end",
            f"파이프라인 완료: {sections_count}개 섹션, {visuals_count}개 시각화",
            {
                "sections_count": sections_count,
                "visuals_count": visuals_count,
                "output_path": output_path
            }
        )
    
    def save_json(self):
        """JSON 형식으로 전체 로그 저장"""
        with open(self.json_file, "w", encoding="utf-8") as f:
            json.dump(self.logs, f, ensure_ascii=False, indent=2)
    
    def generate_summary(self) -> str:
        """로그 요약 생성"""
        summary_lines = []
        summary_lines.append("=" * 80)
        summary_lines.append("파이프라인 실행 요약")
        summary_lines.append("=" * 80)
        
        # 단계별 통계
        stage_counts = {}
        for log in self.logs:
            stage = log["stage"]
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        summary_lines.append("\n[단계별 로그 수]")
        for stage, count in sorted(stage_counts.items()):
            summary_lines.append(f"  {stage}: {count}개")
        
        # 시각화 결정 통계
        visual_decisions = [log for log in self.logs if log["stage"] == "visual_decision"]
        if visual_decisions:
            summary_lines.append("\n[시각화 결정 통계]")
            total_visuals = 0
            visual_types = {"table": 0, "diagram": 0, "image_search": 0, "image_gen": 0}
            
            for log in visual_decisions:
                decision = log["data"]["decision"]
                if decision.get("needs_table"):
                    visual_types["table"] += 1
                    total_visuals += 1
                if decision.get("needs_diagram"):
                    visual_types["diagram"] += 1
                    total_visuals += 1
                if decision.get("needs_image_search"):
                    visual_types["image_search"] += 1
                    total_visuals += 1
                if decision.get("needs_image_gen"):
                    visual_types["image_gen"] += 1
                    total_visuals += 1
            
            summary_lines.append(f"  총 시각화: {total_visuals}개")
            summary_lines.append(f"  - 표: {visual_types['table']}개")
            summary_lines.append(f"  - 다이어그램: {visual_types['diagram']}개")
            summary_lines.append(f"  - 이미지 검색: {visual_types['image_search']}개")
            summary_lines.append(f"  - 이미지 생성: {visual_types['image_gen']}개")
        
        # 검증 통계
        validations = [log for log in self.logs if log["stage"] == "validation"]
        if validations:
            summary_lines.append("\n[검증 통계]")
            valid_count = sum(1 for log in validations if log.get("data", {}).get("is_valid", False))
            invalid_count = len(validations) - valid_count
            scores = [log.get("data", {}).get("score", 0) for log in validations]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            summary_lines.append(f"  총 검증: {len(validations)}회")
            summary_lines.append(f"  적합: {valid_count}회")
            summary_lines.append(f"  부적합: {invalid_count}회")
            summary_lines.append(f"  평균 점수: {avg_score:.2f}")
        
        # 에러 통계
        errors = [log for log in self.logs if log["level"] == "ERROR"]
        if errors:
            summary_lines.append("\n[에러 발생]")
            for log in errors:
                summary_lines.append(f"  [{log['stage']}] {log['message']}")
        
        summary_lines.append("\n" + "=" * 80)
        summary_lines.append(f"로그 파일: {self.log_file}")
        summary_lines.append(f"JSON 파일: {self.json_file}")
        summary_lines.append("=" * 80)
        
        return "\n".join(summary_lines)


# 전역 로거 인스턴스
_logger: PipelineLogger = None


def get_logger() -> PipelineLogger:
    """전역 로거 인스턴스 가져오기"""
    global _logger
    if _logger is None:
        _logger = PipelineLogger()
    return _logger


def reset_logger():
    """로거 리셋 (새 실행 시작 시)"""
    global _logger
    _logger = PipelineLogger()
    return _logger
