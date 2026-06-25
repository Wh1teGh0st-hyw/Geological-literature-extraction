"""值清洗器 — 处理提取数据中的各种非标准格式。

功能:
- 检测并分离误差值（如 "72.5±2.3"）
- 处理低于检测限标记（<LOD, bdl, n.d., n.a., -, --）
- 数值标准化（千分位逗号、中英文数字、科学计数法）
- 异常值标记（超出地球化学合理范围）
"""

import re
from typing import Tuple, Optional, Any
from dataclasses import dataclass
from loguru import logger


@dataclass
class CleanedValue:
    """清洗后的数值。"""
    value: Optional[float] = None
    error: Optional[float] = None
    is_below_lod: bool = False   # 低于检测限
    is_anomalous: bool = False   # 异常值
    original_text: str = ""      # 原始文本
    flags: list = None


class ValueCleaner:
    """地球化学数据值清洗器。"""

    # 低于检测限标记
    LOD_MARKERS = [
        "<lod", "<LOD", "lod", "bdl", "BDL", "b.d.l.",
        "n.d.", "n.a.", "nd", "ND", "N.D.", "n/a", "N/A",
        "na", "NA", "—", "–", "-", "--", "~~", "…", "...",
        "tr.", "trace", "痕量",
    ]

    # 纯数字/符号的非数据行模式
    NON_DATA_PATTERNS = [
        re.compile(r"^[\d\s\.,;:+\-*/=<>|_~#@!&()\[\]{}'""]+$"),  # 全符号+数字
        re.compile(r"^[IVXLCM\.\s]+$"),   # 罗马数字
    ]

    def clean(self, raw_value: Any) -> CleanedValue:
        """清洗单个提取值。

        Args:
            raw_value: 原始值（可能是 str、float、int、None）
        Returns:
            CleanedValue 对象
        """
        result = CleanedValue()

        if raw_value is None:
            return result

        if isinstance(raw_value, (int, float)):
            # 纯数值：直接使用
            try:
                fval = float(raw_value)
                if str(fval) == "nan" or str(fval) == "inf":
                    return result
                result.value = fval
                result.original_text = str(raw_value)
                return result
            except (ValueError, OverflowError):
                return result

        # ── 字符串处理 ──
        text = str(raw_value).strip()
        result.original_text = text

        if not text:
            return result

        # 步骤1: 检测低于检出限
        is_lod = self._check_lod(text)
        if is_lod:
            result.is_below_lod = True

        # 步骤2: 提取纯数字部分（去掉LOD标记前缀）
        cleaned = self._strip_lod_markers(text)

        # 步骤3: 分离误差
        value_str, error_str = self._split_error(cleaned)

        # 步骤4: 数值标准化
        if value_str:
            parsed = self._parse_number(value_str)
            if parsed is not None:
                result.value = parsed

        if error_str:
            parsed_err = self._parse_number(error_str)
            if parsed_err is not None:
                result.error = parsed_err

        return result

    def _check_lod(self, text: str) -> bool:
        """检查是否为低于检测限的值。"""
        t = text.lower().strip()
        for marker in self.LOD_MARKERS:
            if t == marker.lower() or t.startswith(marker.lower()):
                return True
        # 检测 "< 数值" 模式（如 <0.01）
        if re.match(r"^<\s*[\d\.]+", t):
            return True
        return False

    def _strip_lod_markers(self, text: str) -> str:
        """移除 LOD 标记但保留数值。"""
        t = text.strip()

        # "<0.01" → "0.01"
        m = re.match(r"^<\s*([\d\.+\-eE×]+)", t)
        if m:
            return "<" + m.group(1)

        # 移除已知标记前缀
        for marker in ["<lod ", "<LOD ", "bdl ", "BDL ", "tr. "]:
            if t.lower().startswith(marker.lower()):
                return t[len(marker):]

        return t

    def _split_error(self, text: str) -> Tuple[str, Optional[str]]:
        """分离值和误差。

        处理模式:
          "72.5±2.3" → ("72.5", "2.3")
          "72.5(2.3)" → ("72.5", "2.3")  (地质学中括号表示最后几位的误差)
          "72.5 ± 2.3" → ("72.5", "2.3")
          "72.5+2.3/-1.5" → ("72.5", "2.3")  (取正误差)
        """
        # 模式1: ± 符号分 离
        if "±" in text:
            parts = text.split("±", 1)
            return parts[0].strip(), parts[1].strip()

        # 模式2: +/- 分开
        m = re.match(r"^([\d\.]+)\+([\d\.]+)\s*/\s*\-?[\d\.]+", text)
        if m:
            return m.group(1), m.group(2)

        # 模式3: 括号中的误差（只处理纯数字+小数点）
        m = re.match(r"^([\d\.]+)\s*\((\d+)\)$", text)
        if m:
            main_val = m.group(1)
            err_digits = m.group(2)
            # 误差值的小数位对应主值最后几位
            decimal_pos = main_val.find(".")
            if decimal_pos >= 0:
                main_decimals = len(main_val) - decimal_pos - 1
                # 构造误差值
                if len(err_digits) <= main_decimals:
                    err = float(err_digits) * (10 ** (main_decimals - len(err_digits)))
                    err /= 10 ** main_decimals
                    return main_val, str(err)

        return text, None

    def _parse_number(self, text: str) -> Optional[float]:
        """将文本解析为 float。

        处理:
          - 千位分隔符: "1,234.56"
          - 科学计数法: "1.23×10-3", "1.23E-3"
          - 中文负号/减号
          - 百分号
        """
        t = text.strip()

        # 空字符串
        if not t or t in ("<", ">", "<>"):
            return None

        # 保留 < 前缀用于后续LOD标记
        has_lod = t.startswith("<")
        if has_lod:
            t = t[1:]

        # 移除千位分隔符
        t = t.replace(",", "")

        # 百分号检测
        has_percent = t.endswith("%")
        if has_percent:
            t = t[:-1]

        # 科学计数法 ×10^n
        t = t.replace("×10", "e")
        t = t.replace("×10^", "e")
        t = t.replace("×10⁻", "e-")
        t = t.replace("x10", "e")
        t = t.replace("X10", "e")

        # Unicode 上标/下标修复
        t = t.replace("²", "2").replace("³", "3")
        t = t.replace("⁻", "-").replace("⁺", "+")

        # 清理 ~ 和 ≈
        t = t.replace("~", "").replace("≈", "").replace("∼", "")

        try:
            val = float(t)
            # 百分比转换
            if has_percent:
                val = val / 100.0
            return val
        except (ValueError, OverflowError):
            return None

    def is_data_row(self, row_data: list) -> bool:
        """判断一行是否为有效数据行（而非标题/注释/空行）。"""
        if not row_data:
            return False

        # 至少有一个数值
        numeric_count = 0
        for cell in row_data:
            if cell is None:
                continue
            if isinstance(cell, (int, float)):
                numeric_count += 1
            elif isinstance(cell, str):
                try:
                    float(str(cell).strip().replace(",", ""))
                    numeric_count += 1
                except (ValueError, OverflowError):
                    pass

        # 至少有2个数值才视为数据行
        return numeric_count >= 2

    def is_header_row(self, row_data: list) -> bool:
        """判断一行是否为表头行。"""
        if not row_data:
            return False
        text_cells = [c for c in row_data if c is not None and isinstance(c, str) and c.strip()]
        if not text_cells:
            return False

        # 大部分是文本
        header_indicators = 0
        for cell in text_cells:
            cell_str = str(cell).strip()
            # 包含化学元素符号
            if re.search(r"[A-Z][a-z]?\d?[Oo]\d?", cell_str):
                header_indicators += 1
            # 包含中文元素名
            elif re.search(r"[一-鿿]", cell_str):
                header_indicators += 1

        return header_indicators >= max(1, len(text_cells) * 0.5)

    def detect_footnote_start(self, rows: list) -> int:
        """检测脚注开始行索引。返回 -1 表示无脚注。"""
        for i, row in enumerate(rows):
            if row is None:
                continue
            row_text = " ".join(str(c) for c in row if c)
            # 脚注关键词
            if any(kw in row_text for kw in [
                "Note:", "注：", "注释：", "*", "†", "Abbreviations",
                "Abbreviation", "备注",
            ]):
                # 确认后面的行确实有脚注内容
                if i < len(rows) - 1:
                    return i
        return -1
