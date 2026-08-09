"""导出器子包:Excel / Markdown / JSON。"""

from .excel import export_excel, safe_name
from .json_exporter import export_json
from .markdown import export_markdown


def export_all(result, output_dir: str, formats=("xlsx", "md", "json")):
    """按指定格式导出,返回生成的文件路径列表。"""
    paths = []
    exporters = {
        "xlsx": export_excel,
        "md": export_markdown,
        "json": export_json,
    }
    for fmt in formats:
        fn = exporters.get(str(fmt).lower())
        if fn:
            paths.append(fn(result, output_dir))
    return paths


__all__ = ["export_excel", "export_markdown", "export_json", "export_all", "safe_name"]
