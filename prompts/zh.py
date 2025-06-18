import os
import streamlit as st
import re
import random
import logging
import json
from typing import List, Dict, Any, Optional, Tuple, Union

from utils.language_utils import t, get_llm_prompt_instructions, get_current_language

class PromptTemplate:
    def __init__(self, language: str = "zh"):  # Fixed typo: was "lannguage"
        self.language = get_current_language()

    def create_code_generation_prompt_template(
        self,
        code_length: str,
        difficulty_level: str,
        domain: str,
        complexity: str,
        error_count: int,
        error_instructions: str        
    ) -> str:
        """Function-based template for code generation prompt."""
        
        base_prompt = f"""你是一位專業的 Java 程式設計教學專家，負責創建含有刻意錯誤的教學程式碼，供學生練習程式碼評審技能。

    任務：
    為 {domain} 系統生成一個 {code_length} 的 Java 程式，其中包含恰好 {error_count} 個刻意錯誤，用於程式碼評審練習。

    程式碼要求：
    - 創建適合 {difficulty_level} 級別的 {complexity}
    - 所有正確部分都遵循標準 Java 編程慣例
    - 讓程式碼對於 {domain} 應用程式來說顯得真實且專業
    - 除了刻意錯誤外，程式應該結構良好

    錯誤要求：
    - 從下面的特定清單中實作恰好 {error_count} 個錯誤
    - 每個錯誤必須是實際的 Java 程式設計錯誤（不是註解）
    - 錯誤應該可以透過程式碼評審發現
    - 在乾淨版本中不要添加任何關於錯誤的解釋性註解

    要實作的特定錯誤：
    {error_instructions}

    輸出格式：
    1. 帶有錯誤識別註解的註解版本：
    ```java-annotated
    // 你的程式碼與錯誤註解
    ```

    2. 不含錯誤註解的乾淨版本：
    ```java-clean
    // 相同的程式碼，含有相同的錯誤但沒有錯誤註解
    ```

    重要：確保你實作了恰好 {error_count} 個錯誤 - 在提交兩個版本之前驗證此數量。
    """
        
        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_evaluation_prompt_template(
        self,
        error_count: int,
        code: str,
        error_instructions: str        
    ) -> str:
        """Function-based template for evaluation prompt."""
        # Use format() instead of f-strings for complex templates with JSON
        base_prompt = """你是一位 Java 程式碼品質專家，負責分析程式碼以驗證是否正確實作了特定請求的錯誤。

    任務：
    評估提供的 Java 程式碼是否正確實作了來自請求清單的恰好 {error_count} 個特定錯誤。

    要評估的程式碼：
    ```java
    {code}
    ```

    必需錯誤（總共 {error_count} 個）：
    {error_instructions}

    評估過程：

    1. 逐行檢查程式碼以識別與請求清單相符的錯誤
    2. 對於每個相符的錯誤，記錄：
      - 從請求清單中的錯誤類型和名稱
      - 確切的行號
      - 顯示錯誤的程式碼片段
      - 為什麼它符合要求的簡要解釋
    3. 識別程式碼中缺失的任何請求錯誤
    4. 驗證總錯誤數恰好等於 {error_count}


    回應格式：
    ```json
    {{
    "已識別問題": [
        {{
        "錯誤類型": "邏輯錯誤",
        "錯誤名稱": "短路評估的迷思",
        "行號": 42,
        "程式碼片段": "if (obj != null & obj.getValue() > 0) {{ ... }}",
        "解釋": "使用非短路 '&' 運算子而不是 '&&'，導致即使 obj 為 null，obj.getValue() 仍會被評估，可能導致 NullPointerException。"
        }}
    ],
    "遺漏問題": [
        {{
        "錯誤類型": "代碼品質", 
        "錯誤名稱": "程式碼重複",
        "解釋": "未發現重複邏輯或重複程式碼區塊的實例。程式碼重複發生在相似功能被多次實作而不是被提取為可重用方法時。"
        }}
    ],
    "有效": true,
    "反饋": "程式碼成功實作了所有 {error_count} 個請求的錯誤。"
    }}
    ```

    驗證標準：
    - "有效" = true 只有在恰好實作了 {error_count} 個請求錯誤時
    - 僅專注於指定的錯誤，不是一般的程式碼品質問題
    - 確保每個識別的錯誤真正符合請求的錯誤
    """.format(
        error_count=error_count,
        code=code,
        error_instructions=error_instructions
    )
        
        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_regeneration_prompt_template(
        self,
        total_requested: int,
        domain: str,
        missing_text: str,
        found_text: str,
        code: str        
    ) -> str:
        """Function-based template for regeneration prompt."""
        base_prompt = f"""你是一位教學 Java 錯誤創建者，專門在程式碼中刻意引入特定錯誤以用於教學目的。

    任務：
    修改提供的 Java 程式碼，使其包含恰好 {total_requested} 個錯誤 - 不多不少。

    目前狀態：
    - 原始領域：{domain}
    - 需要新增的缺失錯誤：{missing_text}
    - 需要保留的現有錯誤：{found_text}

    修改要求：
    - 僅添加上面列出的特定缺失錯誤
    - 保留所有現有錯誤不做修改
    - 維持原始的 {domain} 結構和功能
    - 每個錯誤必須是實際的 Java 程式碼錯誤，不是註解
    - 不要改進或修復任何現有程式碼

    錯誤實作：
    - 從提供的清單中實作恰好缺失的錯誤
    - 保持所有現有錯誤不變
    - 確保總錯誤數恰好等於 {total_requested}
    - 在註解版本中，用以下格式標記新錯誤：// ERROR: [類型] - [名稱] - [簡要描述]
    - 在乾淨版本中不要添加解釋性註解

    輸出格式：
    1. 帶有錯誤識別註解的註解版本：
    ```java-annotated
    // 你修改的程式碼，僅為新錯誤添加錯誤註解
    ```
    2. 不含錯誤註解的乾淨版本：
    ```java-clean
    // 相同的程式碼，含有相同的錯誤但沒有錯誤註解
    ```

    重要：在提交兩個版本之前，驗證你恰好有 {total_requested} 個總錯誤。

    原始程式碼：
    ```java
    {code}
    ```
    """
        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_review_analysis_prompt_template(
        self,
        code: str,
        problem_count: int,
        problems_text: str,
        student_review: str,
        accuracy_score_threshold: float,
        meaningful_score_threshold: float       
    ) -> str:
        """Function-based template for review analysis prompt."""
        # Use format() for complex templates with JSON
        base_prompt = """你是一位教育評估專家，負責分析學生的 Java 程式碼評審技能。

    任務：
    分析學生在程式碼評審過程中識別已知問題的有效性。

    評審中的程式碼：
    ```java
    {code}
    ```
    已知問題（總共 {problem_count} 個）：
    {problems_text}

    學生的評審：
    ```
    {student_review}
    ```
    評分閾值：

    - 準確性閾值：{accuracy_score_threshold}（正確識別和定位）
    - 有意義閾值：{meaningful_score_threshold}（解釋品質）

    評估過程：

    1. 對於每個已知問題，確定學生是否解決了它
    2. 為相關的學生評論評分（0.0-1.0 量表）：
      - 準確性：他們識別問題和位置的正確程度
      - 有意義：他們解釋為什麼這是問題的程度
    3. 分類規則：問題「已識別」只有在兩個分數都達到閾值時
      - 兩個分數 ≥ 閾值 → "Identified Problems"
      - 否則 → "Missed Problems"

    回應格式：
    ```json
    {{
    "已識別問題": [
        {{
        "問題": "特定已知問題文字",
        "學生評論": "學生的相關評論",
        "準確度": 0.9,
        "有意義性": 0.8,
        "反饋": "對此識別的簡要回饋"
        }}
    ],
    "遺漏問題": [
        {{
        "問題": "特定已知問題文字 - 未解決",
        "提示": "找到此問題的教育提示"
        }}
    ],
    "識別數量": 1,
    "問題總數": {problem_count},
    "識別百分比": 25.0,
    "審查充分性": False,
    "反饋": "整體評估與具體改進建議"
    }}
    ```

    重要要求：
    - 每個問題恰好出現在「已識別」或「遺漏」中一次
    - "Identified Count" 等於 "Identified Problems" 中的項目數
    - 僅使用指定的 JSON 欄位
    """.format(
        code=code,
        problem_count=problem_count,
        problems_text=problems_text,
        student_review=student_review,
        accuracy_score_threshold=accuracy_score_threshold,
        meaningful_score_threshold=meaningful_score_threshold
    )
        
        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_feedback_prompt_template(
        self,
        iteration: int,
        max_iterations: int,
        identified: int,
        total: int,
        accuracy: float,
        remaining: int,
        identified_text: str,
        missed_text: str       
    ) -> str:
        """Function-based template for feedback prompt."""
        base_prompt = f"""你是一位 Java 指導者，提供有針對性的程式碼評審指導，幫助學生提高他們的評審技能。

    學生情境：
    - 評審嘗試 {iteration} 次，共 {max_iterations} 次
    - 發現的問題：{identified}/{total}（{accuracy:.1f}%）
    - 剩餘嘗試次數：{remaining}

    正確識別的問題：
    {identified_text}

    遺漏的問題：
    {missed_text}

    任務：
    創建簡潔、可行的指導（最多 3-4 句話），幫助學生在下次評審嘗試中找到更多問題。

    指導要求：
    - 專注於 1-2 個最重要的改進領域
    - 提供具體策略（要尋找什麼，重點關注哪裡）
    - 既鼓勵又直接
    - 在相關時包含有意義與模糊評論的範例

    有效指導範例：
    "更仔細地查看方法參數和返回類型。有幾個問題涉及型別不匹配，可以透過比較宣告的型別與實際值來發現。同時檢查方法呼叫前的適當 null 處理。"

    無效指導範例：
    "繼續嘗試找到更多問題。程式碼中有幾個你遺漏的問題。在下次評審嘗試中試著更徹底。"

    輸出：
    僅提供指導文字 - 沒有介紹、標題或解釋。
    """

        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt

    def create_comparison_report_prompt_template(
        self,
        total_problems: int,
        identified_count: int,
        accuracy: float,
        missed_count: int,
        identified_text: str,
        missed_text: str,
        progress_info: str        
    ) -> str:
        """Function-based template for comparison report prompt."""
        # Use format() for complex templates with JSON
        base_prompt = f"""你是一位教育評估專家，為 Java 程式設計學生創建綜合性的程式碼評審回饋報告。

    學生表現：
    - 程式碼中的總問題數：{total_problems}
    - 正確識別的問題：{identified_count}（{accuracy:.1f}%）
    - 遺漏的問題：{missed_count}

    正確識別的問題：
    {identified_text}

    遺漏的問題：
    {missed_text}

    {progress_info}

    任務：
    創建一個教育性的 JSON 報告，幫助學生提高他們的 Java 程式碼評審技能。

    報告要求：
    - 使用鼓勵、建設性的語調，同時對需要改進的領域保持誠實
    - 專注於系統性改進模式和可行的指導
    - 包含與他們表現相關的特定 Java 程式碼評審技術
    - 所有回饋都基於提供的實際表現數據
    - 保持個別文字欄位簡潔但有資訊性（最多 2-3 句話）

    輸出格式：
    僅返回具有這些確切欄位的有效 JSON 物件：
    ```json
    {{
      "表現摘要": {{
        "總問題數": {total_problems},
        "識別數量": {identified_count},
        "準確率百分比": {accuracy:.1f},
        "遺漏數量": {missed_count},
        "整體評估": "學生表現的簡要整體評估",
        "完成狀態": "評審的當前狀態（例如，'優秀工作'、'良好進展'、'需要改進'）"
      }},
      "正確識別的問題": [
        {{
          "問題描述": "正確識別問題的描述",
          "讚美評論": "對找到此問題的具體讚揚以及它顯示了他們的哪些技能"
        }}
      ],
      "遺漏問題": [
        {{
          "問題描述": "遺漏問題的描述",
          "為什麼這個錯誤很重要": "為什麼此問題重要的教育解釋",
          "如何找到": "未來如何識別此類問題的具體指導"
        }}
      ],
      "改進建議": [
        {{
          "類別": "改進領域（例如，'邏輯分析'、'語法評審'、'程式碼品質'）",
          "提示": "具體、可行的建議",
          "範例": "說明提示的簡要範例或技術"
        }}
      ],
      "Java特定指導": [
        {{
          "主題": "Java 特定領域（例如，'空指標安全'、'異常處理'、'型別安全'）",
          "指導": "此領域 Java 程式碼評審的具體建議"
        }}
      ],
      "鼓勵與下一步": {{
        "正面反饋": "關於他們進展和優勢的鼓勵性評論",
        "下一個重點領域": "他們在下次評審嘗試中應該專注的內容",
        "學習目標": "基於他們當前表現的關鍵學習目標"
      }},
      "詳細反饋": {{
        "已識別優點": ["他們評審中顯示的具體優勢清單"],
        "改進模式": ["他們遺漏的內容模式，暗示需要重點學習的領域"],
        "審查方法反饋": "對他們整體程式碼評審方法的回饋"
      }}
    }}
    ```
    重要要求：
    - 僅返回 JSON 物件，不含額外文字或格式
    - 如果沒有正確識別或遺漏的問題，使用空陣列 []
    - 確保所有 JSON 字串都正確轉義且有效
    - 所有回饋都基於提供的表現數據
    """.format(
        total_problems=total_problems,
        identified_count=identified_count,
        accuracy=accuracy,
        missed_count=missed_count,
        identified_text=identified_text,
        missed_text=missed_text,
        progress_info=progress_info
    )

        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt