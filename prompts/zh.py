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
        base_prompt = f"""你是一位 Java 程式碼品質專家，負責分析程式碼以驗證是否正確實作了特定請求的錯誤。

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
        "程式碼片段": "if (obj != null & obj.getValue() > 0)",
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
    """
        
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
      base_prompt = f"""你是一位教育評估專家，負責分析學生的 Java 程式碼評審技能。你必須非常嚴格地評估學生的評論。

  任務：
  分析學生在程式碼評審過程中識別已知問題的有效性。你必須非常嚴格和精確地評分。

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
  - 準確性閾值：{accuracy_score_threshold}（必須正確識別錯誤類型和位置）
  - 有意義性閾值：{meaningful_score_threshold}（必須清楚解釋為什麼是問題）

  ⚠️ 極其嚴格的評分與分類規則（絕對不能違反）：

  A. 核心識別要求（Core Identification Requirements）
    1. 學生評論必須同時滿足以下所有條件才能被視為「具體識別」：
        a) 明確提及錯誤類型的關鍵詞（例如：「使用 == 比較字串」、「空指標」、「邏輯錯誤」）
        b) 正確指出錯誤的位置（方法名、行號、或具體程式碼片段）
        c) 評論內容與已知問題實質相符
        
    2. 如果學生評論不符合上述任一條件，必須：
        - 準確度評分：<= 0.3（最高不超過0.3）
        - 有意義性評分：<= 0.3（最高不超過0.3）
        - 分類：必須放入「遺漏問題」
        - 不得計入「識別數量」

  B. 評分嚴格性（Scoring Strictness）
    1. 準確度評分標準（極其嚴格）：
        - 1.0：完全正確識別錯誤類型、位置和原因
        - 0.8-0.9：正確識別錯誤類型和位置，但原因說明略有不足
        - 0.6-0.7：識別錯誤類型正確，但位置不夠精確
        - 0.4-0.5：部分相關但有明顯錯誤或遺漏
        - 0.1-0.3：幾乎不相關或完全錯誤
        - 0.0：完全無關或空白
    
    2. 有意義性評分標準（極其嚴格）：
        - 1.0：清楚解釋為什麼是問題，說明潛在影響或風險
        - 0.8-0.9：解釋為什麼是問題，但不夠深入
        - 0.6-0.7：簡單說明是問題，但缺乏深度
        - 0.4-0.5：只是指出位置，沒有解釋原因
        - 0.1-0.3：空洞或重複的評論
        - 0.0：完全無意義或空白

    3. 嚴格禁止「慷慨評分」：
        - 絕對不要給予「好意分數」
        - 如果有任何疑問，給較低分數
        - 寧可低估也不要高估學生能力

  C. 門檻值保護（Threshold Protection）
    1. 只有當學生評論同時滿足以下條件時，分數才能達到或超過門檻值：
        - 明確指出錯誤類型（例如：「使用 == 而非 equals()」）
        - 清楚說明為什麼這是問題（例如：「== 比較記憶體位址，不比較內容」）
        - 準確指出位置（方法名或行號）
    
    2. 如果學生評論缺少上述任一要素：
        - 兩個分數都必須 < 門檻值
        - 必須放入「遺漏問題」

  D. 無效評論判定（Invalid Comment Detection）
    學生評論屬於以下任一情況時，視為「未識別」：
    - 重複字詞或感嘆語（例如：「這裡有問題」、「不對」）
    - 錯誤的行號或方法名
    - 與已知問題完全無關的描述
    - 空洞的泛泛而談（例如：「程式碼品質不好」）
    - 只說「有錯誤」但沒說是什麼錯誤
    
    處理方式：
    - 準確度：<= 0.2
    - 有意義性：<= 0.2
    - 分類：「遺漏問題」
    - 「學生評論」欄位：記錄為「未具體識別」或「評論不相關」

  E. 強制分類規則（Mandatory Classification Rules）
    1. 分類判定（絕對規則，不可違反）：
        IF (準確度 >= {accuracy_score_threshold} AND 有意義性 >= {meaningful_score_threshold}):
          → 必須放入「已識別問題」
          → 必須計入「識別數量」
        ELSE:
          → 必須放入「遺漏問題」
          → 不得計入「識別數量」
    
    2. 互斥性原則：
        - 每個已知問題必須恰好出現在一個列表中
        - 絕對不能同時出現在「已識別問題」和「遺漏問題」中
        - 絕對不能遺漏任何已知問題

  F. 位置與邏輯一致性（Position and Logic Consistency）
    1. 如果學生評論聲稱的位置與實際錯誤位置不符：
        - 準確度：<= 0.3
        - 分類：「遺漏問題」
    
    2. 如果學生評論的邏輯與已知問題的錯誤邏輯矛盾：
        - 準確度：<= 0.4
        - 有意義性：<= 0.4
        - 分類：「遺漏問題」

  G. 評分前自我檢查（Pre-Output Validation）
    在輸出 JSON 之前，必須執行以下檢查：
    1. 確認每個「已識別問題」的分數都 >= 門檻值
    2. 確認每個「遺漏問題」的分數至少有一個 < 門檻值
    3. 確認「識別數量」= 「已識別問題」陣列長度
    4. 確認所有 {problem_count} 個已知問題都被分類
    5. 確認沒有問題同時出現在兩個列表中

  回應格式（只允許以下 JSON 欄位與結構）：
  {{
    "已識別問題": [
      {{
        "問題": "已知問題的完整描述",
        "學生評論": "學生的相關評論（必須實質相符）",
        "準確度": <必須 >= {accuracy_score_threshold}>,
        "有意義性": <必須 >= {meaningful_score_threshold}>,
        "反饋": "具體說明學生評論如何正確識別此問題，引用學生使用的關鍵詞和位置線索"
      }}
    ],
    "遺漏問題": [
      {{
        "問題": "已知問題的完整描述",
        "學生評論": "學生的嘗試（如果有）或「未提及」或「評論不相關」",
        "準確度": <實際分數（必須 < {accuracy_score_threshold} 或有意義性 < {meaningful_score_threshold}）>,
        "有意義性": <實際分數>,
        "提示": "具體指導：告訴學生應該在哪個方法/程式碼片段尋找此問題，以及應該注意什麼錯誤模式"
      }}
    ],
    "識別數量": <必須等於「已識別問題」陣列的長度，不是學生評論的總數>,
    "問題總數": {problem_count},
    "識別百分比": <(識別數量 / 問題總數) * 100>,
    "審查充分性": <識別數量 == 問題總數>,
    "反饋": "整體評估：具體指出學生在哪些類型的錯誤上做得好，哪些類型需要改進。避免空話，給出可操作的建議。"
  }}

  ⚠️ 最終提醒（Critical Reminders）：
  1. 寧可嚴格也不要寬鬆
  2. 如果學生評論模糊不清，給低分
  3. 如果學生評論位置錯誤，給低分
  4. 如果學生評論沒有解釋原因，有意義性必須 < 門檻值
  5. 「識別數量」只能計算真正正確識別的問題
  6. 分數低於門檻值的必須放入「遺漏問題」
  7. 每個已知問題必須被分類一次且僅一次
  8. 在輸出前必須驗證所有規則都被遵守
  """
      
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
        missed_text: str        
    ) -> str:
        """Function-based template for comparison report prompt - FIXED: Use only f-string, remove .format()"""
        # FIXED: Use only f-string, removed the incorrect .format() call
        base_prompt = f"""你是一位教育評估專家，為 Java 程式設計學生創建綜合性的程式碼評審回饋報告。

    學生表現：
    - 程式碼中的總問題數：{total_problems}
    - 正確識別的問題：{identified_count}（{accuracy:.1f}%）
    - 遺漏的問題：{missed_count}

    正確識別的問題：
    {identified_text}

    遺漏的問題：
    {missed_text}

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
    """
        
        language_instructions = get_llm_prompt_instructions(self.language)
        if language_instructions:
            return f"{language_instructions}\n\n{base_prompt}"
        return base_prompt