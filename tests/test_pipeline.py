"""Mock 端到端管线测试:解析 -> 分析 -> 生成 -> 评审 -> 导出。"""

from pathlib import Path

from testcase_agent.config import AppConfig
from testcase_agent.pipeline.agent import TestCaseAgent

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
OUT = Path(__file__).resolve().parent.parent / "output_test"


def _mock_config() -> AppConfig:
    cfg = AppConfig.load(None)
    cfg.pipeline.mock_mode = True
    return cfg


class TestPipelineE2E:
    def test_full_pipeline(self, tmp_path):
        cfg = _mock_config()
        agent = TestCaseAgent(cfg)
        result = agent.run([str(SAMPLES / "sample_prd.md")], output_dir=str(tmp_path))

        assert result.product_name
        assert len(result.analysis.test_points) >= 8
        assert len(result.cases) >= 10
        assert result.review is not None
        # case_id 全局唯一连续
        ids = [c.case_id for c in result.cases]
        assert ids == sorted(ids) and len(set(ids)) == len(ids)
        # 字段完整性
        for c in result.cases:
            assert c.steps and c.expected and c.title and c.priority in ("P0", "P1", "P2", "P3")
            assert c.case_type

    def test_review_disabled(self, tmp_path):
        cfg = _mock_config()
        cfg.pipeline.review_enabled = False
        agent = TestCaseAgent(cfg)
        result = agent.run([str(SAMPLES / "sample_prd.md")], output_dir=str(tmp_path),
                           review=False)
        assert result.review is None
        assert len(result.cases) > 0

    def test_exports_generated(self, tmp_path):
        cfg = _mock_config()
        agent = TestCaseAgent(cfg)
        agent.run([str(SAMPLES / "sample_prd.md")], output_dir=str(tmp_path))
        files = list(tmp_path.glob("*_测试用例.*"))
        exts = {f.suffix for f in files}
        assert ".xlsx" in exts and ".md" in exts and ".json" in exts

    def test_no_files_raises(self):
        agent = TestCaseAgent(_mock_config())
        import pytest
        with pytest.raises(ValueError):
            agent.run([])

    def test_progress_callback(self, tmp_path):
        cfg = _mock_config()
        agent = TestCaseAgent(cfg)
        stages = []
        agent.on_progress(lambda msg: stages.append(msg))
        agent.run([str(SAMPLES / "sample_prd.md")], output_dir=str(tmp_path))
        assert any("阶段 1/3" in s for s in stages)
        assert any("阶段 3/3" in s for s in stages)
        assert any("完成" in s for s in stages)
