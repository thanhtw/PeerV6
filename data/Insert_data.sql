-- Enhanced Database Inserts for Java Peer Review Training System
-- Version: 2.0 with Comprehensive Badge System and Error Data

-- Insert error categories first
INSERT INTO error_categories (name_en, name_zh, description_en, description_zh, icon, sort_order) VALUES
('Logical Errors', '邏輯錯誤', 'Errors in program logic and algorithmic thinking', '程式邏輯和演算法思維錯誤', '🧠', 1),
('Syntax Errors', '語法錯誤', 'Java syntax and compilation errors', 'Java語法和編譯錯誤', '📝', 2),
('Code Quality', '程式碼品質', 'Code style, readability and best practices', '程式碼風格、可讀性和最佳實踐', '⭐', 3),
('Standard Violation', '標準違規', 'Java coding standards and conventions', 'Java編碼標準和慣例', '📏', 4),
('Java Specific', 'Java特定錯誤', 'Java-specific language features and pitfalls', 'Java特定語言功能和陷阱', '☕', 5);

-- Insert Java errors (comprehensive set using consistent format)
INSERT INTO java_errors (error_code, category_id, error_name_en, error_name_zh, description_en, description_zh, implementation_guide_en, implementation_guide_zh, difficulty_level, tags, examples) VALUES
-- Logical Errors
('LOG001', 1, 'Off-by-one Error', '差一錯誤', 'Common mistake in loop boundaries or array indexing', '迴圈邊界或陣列索引中的常見錯誤', 'Check loop conditions and array bounds carefully', '仔細檢查迴圈條件和陣列邊界', 'easy', '["loops", "arrays", "indexing", "boundaries"]', '[{"wrong": "for(int i=0; i<=array.length; i++)", "correct": "for(int i=0; i<array.length; i++)"}]'),

('LOG002', 1, 'Null check after dereference', '解引用後檢查null', 'Accessing an object''s methods or fields before checking if it''s null', '在檢查物件是否為null之前存取其方法或欄位', 'Write code that uses an object and then checks if it''s null: ''if(object.getValue() > 0 && object != null)'' which causes NullPointerException if object is null', '編寫先使用物件再檢查null的程式碼：''if(object.getValue() > 0 && object != null)''，若object為null會導致異常', 'medium', '["null", "safety", "exceptions"]', '[{"wrong": "if(object.getValue() > 0 && object != null)", "correct": "if(object != null && object.getValue() > 0)"}]'),

('LOG003', 1, 'Unintended integer division', '意外的整數除法', 'Integer division that truncates decimal results when floating-point division was intended', '當需要浮點數除法時，整數除法會截斷小數結果', 'Divide two integers where decimal precision is needed: ''double result = 5 / 2;'' gives 2.0 instead of 2.5', '在需要小數精度時除以兩個整數：''double result = 5 / 2;''得到2.0而非2.5', 'medium', '["division", "casting", "precision"]', '[{"wrong": "double result = 5 / 2;", "correct": "double result = 5.0 / 2;"}]'),

('LOG004', 1, 'Ignoring method return values', '忽略方法回傳值', 'Not checking or using the return value of a method, especially for methods that return status or modified values', '未檢查或使用方法的回傳值，特別是回傳狀態或修改值的方法', 'Call string.replace() without assigning the result: ''myString.replace("old", "new");'' instead of ''myString = myString.replace("old", "new");''', '呼叫string.replace()但未指派結果：''myString.replace("old", "new");''而非''myString = myString.replace("old", "new");''', 'medium', '["return-values", "immutable", "strings"]', '[{"wrong": "myString.replace(\\"old\\", \\"new\\");", "correct": "myString = myString.replace(\\"old\\", \\"new\\");"}]'),

('LOG005', 1, 'Incorrect equals/hashCode implementation', '錯誤的equals/hashCode實作', 'Overriding equals() without overriding hashCode() or implementing them inconsistently', '覆寫equals()而未覆寫hashCode()，或實作不一致', 'Override only equals() method without hashCode(), or use different fields in equals() and hashCode() implementations', '只覆寫equals()方法而未覆寫hashCode()，或在equals()和hashCode()中使用不同欄位', 'hard', '["equals", "hashCode", "contracts"]', '[{"advice": "Always override both equals() and hashCode() together"}]'),

('LOG006', 1, 'Misunderstanding of short-circuit evaluation', '短路求值的誤解', 'Not utilizing or misunderstanding how && and || short-circuit, leading to potential errors or inefficient code', '未利用或誤解&&和||的短路特性，導致潛在錯誤或低效程式碼', 'Use ''&'' or ''|'' instead of ''&&'' or ''||'' when short-circuiting is needed to prevent NullPointerException: ''if(obj != null & obj.getValue() > 0)''', '當需要短路來防止NullPointerException時使用''&''或''|''而非''&&''或''||''：''if(obj != null & obj.getValue() > 0)''', 'hard', '["short-circuit", "operators", "evaluation"]', '[{"wrong": "if(obj != null & obj.getValue() > 0)", "correct": "if(obj != null && obj.getValue() > 0)"}]'),

('LOG007', 1, 'Race conditions in multi-threaded code', '多執行緒程式碼中的競爭條件', 'Incorrect synchronization leading to unpredictable behavior when multiple threads access shared resources', '不正確的同步導致多個執行緒存取共享資源時行為不可預測', 'Access shared variables without proper synchronization or locks, or use non-atomic operations in concurrent contexts', '在沒有適當同步或鎖的情況下存取共享變數，或在併發上下文中使用非原子操作', 'hard', '["threading", "synchronization", "concurrency"]', '[{"advice": "Use synchronized blocks, locks, or atomic operations for shared data"}]'),

('LOG008', 1, 'String comparison using ==', '使用==比較字串', 'Comparing String objects with == instead of the equals() method', '使用==而非equals()方法比較String物件', 'Compare strings with == instead of equals(): ''if(str1 == str2)'' instead of ''if(str1.equals(str2))''', '使用==而非equals()比較字串：''if(str1 == str2)''而非''if(str1.equals(str2))''', 'easy', '["strings", "equals", "comparison"]', '[{"wrong": "if(str1 == str2)", "correct": "if(str1.equals(str2))"}]'),

('LOG009', 1, 'Side effects in assertions', '斷言中的副作用', 'Including operations with side effects in assertions, which may not execute when assertions are disabled', '在斷言中包含有副作用的操作，當斷言被禁用時可能不會執行', 'Write assertions that modify state: ''assert (x = calculateValue()) > 0;'' where x is being assigned a value', '編寫修改狀態的斷言：''assert (x = calculateValue()) > 0;''其中x被賦值', 'medium', '["assertions", "side-effects", "debugging"]', '[{"wrong": "assert (x = calculateValue()) > 0;", "correct": "x = calculateValue(); assert x > 0;"}]'),

('LOG010', 1, 'Missing break in switch statements', 'switch語句中缺少break', 'Forgetting break statements in switch cases, causing unintended fall-through to subsequent cases', '忘記在switch case中加break語句，導致意外地繼續執行後續case', 'Create a switch statement without break statements between cases, leading to execution of multiple case blocks', '建立沒有break語句的switch語句，導致執行多個case區塊', 'medium', '["switch", "break", "fall-through"]', '[{"advice": "Always include break statements unless fall-through is intentional"}]'),

('LOG011', 1, 'Using assignment instead of comparison', '使用賦值而非比較', 'Using = (assignment) instead of == (comparison) in a conditional statement', '在條件語句中使用=（賦值）而非==（比較）', 'Use assignment in condition: ''if(x = 5)'' instead of ''if(x == 5)'', which assigns 5 to x and then evaluates to true', '在條件中使用賦值：''if(x = 5)''而非''if(x == 5)''，會將5賦值給x然後求值為true', 'easy', '["assignment", "comparison", "operators"]', '[{"wrong": "if(x = 5)", "correct": "if(x == 5)"}]'),

('LOG012', 1, 'Order of operations misunderstanding', '運算順序誤解', 'Incorrect assumptions about operator precedence leading to unexpected calculation results', '對運算子優先順序的錯誤假設導致意外的計算結果', 'Write expressions without parentheses where the order of operations matters: ''a + b * c'' expecting (a + b) * c', '編寫沒有括號但運算順序很重要的表達式：''a + b * c''期望(a + b) * c', 'medium', '["precedence", "operators", "parentheses"]', '[{"wrong": "a + b * c", "correct": "(a + b) * c"}]'),

-- Syntax Errors
('SYN001', 2, 'Missing semicolons', '缺少分號', 'Forgetting to terminate statements with semicolons, causing compilation errors', '忘記用分號終止語句，導致編譯錯誤', 'Omit semicolons at the end of statements: ''int x = 5'' instead of ''int x = 5;''', '在語句末尾省略分號：''int x = 5''而非''int x = 5;''', 'easy', '["semicolon", "syntax", "compilation"]', '[{"wrong": "int x = 5", "correct": "int x = 5;"}]'),

('SYN002', 2, 'Unbalanced brackets or parentheses', '括號不平衡', 'Having mismatched opening and closing brackets, braces, or parentheses in code', '程式碼中的開括號和閉括號、大括號或圓括號不匹配', 'Create code with unbalanced brackets: ''if (condition) { doSomething();'' without the closing brace', '建立括號不平衡的程式碼：''if (condition) { doSomething();''沒有閉括號', 'easy', '["brackets", "braces", "parentheses"]', '[{"wrong": "if (condition) { doSomething();", "correct": "if (condition) { doSomething(); }"}]'),

('SYN003', 2, 'Incorrect method declaration', '錯誤的方法宣告', 'Syntax errors in method declarations, such as missing return types or incorrect modifiers', '方法宣告中的語法錯誤，如缺少回傳型別或錯誤的修飾符', 'Declare a method without a return type: ''public calculateTotal(int x, int y) { return x + y; }'' instead of ''public int calculateTotal(int x, int y) { return x + y; }''', '宣告沒有回傳型別的方法：''public calculateTotal(int x, int y) { return x + y; }''而非''public int calculateTotal(int x, int y) { return x + y; }''', 'medium', '["methods", "declaration", "return-type"]', '[{"wrong": "public calculateTotal(int x, int y)", "correct": "public int calculateTotal(int x, int y)"}]'),

('SYN004', 2, 'Invalid variable declarations', '無效的變數宣告', 'Syntax errors in variable declarations, such as missing types or invalid identifiers', '變數宣告中的語法錯誤，如缺少型別或無效識別符', 'Declare variables with invalid syntax: ''int 2count = 10;'' using identifiers that start with numbers, or ''count = 5;'' without specifying type for a new variable', '使用無效語法宣告變數：''int 2count = 10;''使用以數字開頭的識別符，或''count = 5;''未指定新變數的型別', 'easy', '["variables", "declaration", "identifiers"]', '[{"wrong": "int 2count = 10;", "correct": "int count2 = 10;"}]'),

('SYN005', 2, 'Type mismatch in assignment', '賦值中的型別不匹配', 'Assigning values of incompatible types without proper casting', '在沒有適當轉型的情況下賦值不相容的型別', 'Assign incompatible types without casting: ''int x = "Hello";'' or ''String s = 42;''', '不經轉型賦值不相容型別：''int x = "Hello";''或''String s = 42;''', 'easy', '["types", "assignment", "casting"]', '[{"wrong": "int x = \\"Hello\\";", "correct": "String x = \\"Hello\\";"}]'),

('SYN006', 2, 'Using keywords as identifiers', '使用關鍵字作為識別符', 'Attempting to use Java reserved keywords as variable, method, or class names', '嘗試將Java保留關鍵字用作變數、方法或類名', 'Try to use reserved words as identifiers: ''int class = 10;'' or ''void public() { }''', '嘗試使用保留字作為識別符：''int class = 10;''或''void public() { }''', 'easy', '["keywords", "identifiers", "reserved"]', '[{"wrong": "int class = 10;", "correct": "int className = 10;"}]'),

('SYN007', 2, 'Missing return statement', '缺少return語句', 'Not providing a return statement in a method that declares a return type', '在宣告回傳型別的方法中未提供return語句', 'Create a non-void method without a return statement: ''public int getValue() { int x = 10; }'' without returning x', '建立沒有return語句的非void方法：''public int getValue() { int x = 10; }''沒有回傳x', 'easy', '["return", "methods", "compilation"]', '[{"wrong": "public int getValue() { int x = 10; }", "correct": "public int getValue() { int x = 10; return x; }"}]'),

('SYN008', 2, 'Illegal modifiers', '非法修飾符', 'Using incompatible or redundant modifiers for classes, methods, or variables', '對類、方法或變數使用不相容或冗餘的修飾符', 'Use conflicting modifiers: ''private public void method()'' or ''final abstract class MyClass''', '使用衝突的修飾符：''private public void method()''或''final abstract class MyClass''', 'medium', '["modifiers", "access", "compilation"]', '[{"wrong": "private public void method()", "correct": "public void method()"}]'),

-- Code Quality Issues
('CQ001', 3, 'Magic numbers', '魔術數字', 'Using literal numbers in code instead of named constants, reducing readability and maintainability', '在程式碼中使用字面數字而非具名常數，降低可讀性和維護性', 'Hardcode numeric values: ''if(count > 1000)'' or ''for(int i=0; i<365; i++)'' instead of using named constants', '硬編碼數值：''if(count > 1000)''或''for(int i=0; i<365; i++)''而非使用具名常數', 'easy', '["constants", "readability", "maintainability"]', '[{"wrong": "if(count > 1000)", "correct": "private static final int MAX_COUNT = 1000; if(count > MAX_COUNT)"}]'),

('CQ002', 3, 'Long method', '過長的方法', 'Methods that are excessively long and try to do too many things, violating the Single Responsibility Principle', '過長且承擔過多責任的方法，違反單一職責原則', 'Create methods with more than 50 lines that perform multiple responsibilities instead of breaking them into smaller, focused methods', '建立超過50行且執行多項職責的方法，而非將其拆分為更小、專注的方法', 'medium', '["methods", "single-responsibility", "refactoring"]', '[{"advice": "Break methods longer than 20-30 lines into smaller methods"}]'),

('CQ003', 3, 'Code duplication', '程式碼重複', 'Repeated code blocks that could be refactored into shared methods or utilities', '重複的程式碼區塊，可以重構為共享方法或工具', 'Copy-paste similar logic in multiple places instead of extracting common logic into separate methods', '在多個地方複製貼上相似邏輯，而非將共通邏輯提取到獨立方法中', 'medium', '["duplication", "refactoring", "dry"]', '[{"advice": "Extract common logic into reusable methods"}]'),

('CQ004', 3, 'Deep nesting', '過深巢狀', 'Excessive levels of nested conditionals or loops, making code hard to read and maintain', '過多層級的巢狀條件或迴圈，使程式碼難以閱讀和維護', 'Create deeply nested if-else statements or loops with 4+ levels of indentation instead of using early returns or extracted methods', '建立深度巢狀的if-else語句或4+層縮排的迴圈，而非使用早期回傳或提取方法', 'medium', '["nesting", "readability", "complexity"]', '[{"advice": "Use early returns and extract methods to reduce nesting"}]'),

('CQ005', 3, 'Poor exception handling', '糟糕的例外處理', 'Catching exceptions that are too broad or empty catch blocks that swallow exceptions without proper handling', '捕獲過於廣泛的例外或空的catch區塊，在沒有適當處理的情況下吞噬例外', 'Use catch(Exception e) {} with empty body, hiding all errors, or catch overly broad exceptions without specific handling', '使用空內容的catch(Exception e) {}，隱藏所有錯誤，或捕獲過於廣泛的例外而沒有特定處理', 'medium', '["exceptions", "error-handling", "debugging"]', '[{"wrong": "catch(Exception e) {}", "correct": "catch(SpecificException e) { logger.error(\\"Error\\", e); }"}]'),

('CQ006', 3, 'Missing logging', '缺少日誌記錄', 'Inadequate or missing logging, especially for errors, making troubleshooting difficult', '日誌記錄不足或缺失，特別是錯誤日誌，使故障排除變得困難', 'Create catch blocks that don''t log exceptions, or omit logging of important application events and state changes', '建立不記錄例外的catch區塊，或省略重要應用程式事件和狀態變更的日誌記錄', 'easy', '["logging", "debugging", "monitoring"]', '[{"advice": "Add appropriate logging for errors and important events"}]'),

('CQ007', 3, 'Inappropriate comments', '不當的註釋', 'Comments that are misleading, outdated, or simply restate what the code does without adding value', '誤導性、過時或僅重述程式碼功能而不增加價值的註釋', 'Write comments that just repeat the code: ''// increment counter'' for ''counter++'', or leave outdated comments that no longer match the code', '編寫僅重複程式碼的註釋：對''counter++''寫''// increment counter''，或留下不再符合程式碼的過時註釋', 'easy', '["comments", "documentation", "clarity"]', '[{"wrong": "// increment counter\\ncounter++;", "correct": "// Update user session timeout\\ncounter++;"}]'),

('CQ008', 3, 'Poor variable naming', '變數命名不佳', 'Using unclear, ambiguous, or overly abbreviated variable names that don''t convey their purpose', '使用不清楚、模糊或過度縮寫的變數名稱，不能傳達其用途', 'Use names like ''x'', ''temp'', or ''data'' that don''t clearly indicate the purpose or content of the variable', '使用如''x''、''temp''或''data''等不能清楚表明變數用途或內容的名稱', 'easy', '["naming", "readability", "clarity"]', '[{"wrong": "int x = getUserCount();", "correct": "int activeUserCount = getUserCount();"}]'),

('CQ009', 3, 'Law of Demeter violations', '迪米特法則違規', 'Violating the principle that an object should only interact with its immediate neighbors, creating tight coupling', '違反物件應只與其直接鄰居互動的原則，造成緊密耦合', 'Create method chains like ''object.getX().getY().doZ()'' instead of having objects only communicate with direct dependencies', '建立如''object.getX().getY().doZ()''的方法鏈，而非讓物件只與直接依賴項通信', 'hard', '["coupling", "design", "dependencies"]', '[{"wrong": "object.getX().getY().doZ()", "correct": "object.performAction()"}]'),

('CQ010', 3, 'Not using appropriate collections', '未使用適當的集合', 'Using the wrong collection type for the operations being performed, leading to inefficient code', '對執行的操作使用錯誤的集合型別，導致低效的程式碼', 'Use ArrayList when frequent insertions/deletions are needed (LinkedList would be better), or use List when set operations are required', '當需要頻繁插入/刪除時使用ArrayList（LinkedList會更好），或當需要集合操作時使用List', 'medium', '["collections", "performance", "data-structures"]', '[{"advice": "Choose collections based on access patterns: ArrayList for random access, LinkedList for frequent insertions"}]'),

('CQ011', 3, 'Excessive class coupling', '過度類耦合', 'Classes that are too interdependent, making the system fragile and difficult to modify', '類別過於相互依賴，使系統脆弱且難以修改', 'Create classes that directly reference many other concrete classes instead of using interfaces, dependency injection, or other decoupling patterns', '建立直接引用許多其他具體類的類，而非使用介面、依賴注入或其他解耦模式', 'hard', '["coupling", "design", "interfaces"]', '[{"advice": "Use interfaces and dependency injection to reduce coupling"}]'),

('CQ012', 3, 'Not using try-with-resources', '未使用try-with-resources', 'Not using try-with-resources for AutoCloseable resources, risking resource leaks', '對AutoCloseable資源未使用try-with-resources，有資源洩漏風險', 'Manually close resources with finally blocks instead of using try-with-resources: ''try { FileReader fr = new FileReader(file); ... } finally { fr.close(); }''', '使用finally區塊手動關閉資源而非使用try-with-resources：''try { FileReader fr = new FileReader(file); ... } finally { fr.close(); }''', 'medium', '["resources", "memory", "cleanup"]', '[{"wrong": "try { FileReader fr = new FileReader(file); } finally { fr.close(); }", "correct": "try (FileReader fr = new FileReader(file)) { }"}]'),

-- Standard Violations
('STD001', 4, 'Inconsistent naming conventions', '不一致的命名慣例', 'Not following standard Java naming conventions for classes, methods, variables, and constants', '未遵循Java類、方法、變數和常數的標準命名慣例', 'Use incorrect naming: ''class myClass'' (lowercase), ''public void GetValue()'' (uppercase method), ''final int maxValue = 100'' (non-uppercase constant)', '使用錯誤命名：''class myClass''（小寫），''public void GetValue()''（大寫方法），''final int maxValue = 100''（非大寫常數）', 'easy', '["naming", "conventions", "style"]', '[{"wrong": "class myClass, void GetValue(), final int maxValue", "correct": "class MyClass, void getValue(), final int MAX_VALUE"}]'),

('STD002', 4, 'Improper indentation', '縮排不當', 'Inconsistent or incorrect code indentation that reduces readability', '縮排不一致或錯誤，降低可讀性', 'Use inconsistent or missing indentation in code blocks, especially nested ones', '在程式碼區塊中使用不一致或缺少縮排，特別是巢狀區塊', 'easy', '["formatting", "indentation", "readability"]', '[{"advice": "Use consistent 4-space or 1-tab indentation throughout"}]'),

('STD003', 4, 'Unorganized imports', '未組織的import', 'Import statements that are not properly organized or contain unused imports', 'Import語句未適當組織或包含未使用的import', 'Import classes that aren''t used, use wildcard imports unnecessarily, or leave imports unorganized (not grouped by package)', 'Import未使用的類，不必要地使用萬用字元import，或保持import未組織（未按套件分組）', 'easy', '["imports", "organization", "cleanup"]', '[{"advice": "Group imports by package and remove unused ones"}]'),

('STD004', 4, 'Missing file headers', '缺少檔案標頭', 'Source files without standard header comments describing purpose, author, and license information', '原始檔沒有描述用途、作者和授權資訊的標準標頭註釋', 'Omit file header documentation that includes information about the class purpose, creation date, author, and copyright', '省略包含類用途、建立日期、作者和版權資訊的檔案標頭文件', 'easy', '["documentation", "headers", "standards"]', '[{"advice": "Include standard file headers with class purpose and author info"}]'),

('STD005', 4, 'Line length violations', '行長度違規', 'Lines of code that exceed the recommended maximum length (typically 80-120 characters)', '超過建議最大長度（通常80-120字符）的程式碼行', 'Write extremely long lines of code that require horizontal scrolling instead of breaking them into multiple lines', '編寫需要水平滾動的極長程式碼行，而非將其拆分為多行', 'easy', '["formatting", "line-length", "readability"]', '[{"advice": "Keep lines under 120 characters, break long statements"}]'),

('STD006', 4, 'Inconsistent brace placement', '括號放置不一致', 'Placing opening and closing braces inconsistently throughout the codebase', '在整個程式碼庫中不一致地放置開括號和閉括號', 'Mix different brace styles: ''if (condition) {'' and ''if (condition)\n{'' in the same codebase', '混合不同的括號風格：在同一程式碼庫中使用''if (condition) {''和''if (condition)\n{''', 'easy', '["formatting", "braces", "consistency"]', '[{"advice": "Choose one brace style and use it consistently"}]'),

('STD007', 4, 'Unconventional package structure', '非慣例的套件結構', 'Not following standard package naming and organization conventions', '未遵循標準套件命名和組織慣例', 'Use non-conventional package names like uppercase packages, or place classes in inappropriate packages', '使用非慣例的套件名稱如大寫套件，或將類放在不適當的套件中', 'medium', '["packages", "naming", "organization"]', '[{"advice": "Use lowercase package names following reverse domain convention"}]'),

('STD008', 4, 'Ignoring code analyzer warnings', '忽略程式碼分析器警告', 'Suppressing or ignoring warnings from static code analyzers without proper justification', '在沒有適當理由的情況下抑制或忽略靜態程式碼分析器的警告', 'Add @SuppressWarnings annotations without comments explaining why the warning is being suppressed', '添加@SuppressWarnings註解而沒有註釋解釋為何抑制警告', 'medium', '["warnings", "analysis", "justification"]', '[{"wrong": "@SuppressWarnings(\\"unused\\")", "correct": "@SuppressWarnings(\\"unused\\") // Field used by reflection"}]'),

-- Java Specific Errors
('JS001', 5, 'Raw type usage', '使用原始型別', 'Using raw types instead of parameterized types, bypassing generic type safety', '使用原始型別而非參數化型別，繞過泛型型別安全', 'Use ''List list = new ArrayList();'' instead of ''List<String> list = new ArrayList<>();'', losing type safety', '使用''List list = new ArrayList();''而非''List<String> list = new ArrayList<>();''，失去型別安全', 'medium', '["generics", "type-safety", "collections"]', '[{"wrong": "List list = new ArrayList();", "correct": "List<String> list = new ArrayList<>();"}]'),

('JS002', 5, 'Collection modification during iteration', '疊代期間修改集合', 'Modifying a collection while iterating over it with a for-each loop, causing ConcurrentModificationException', '在使用for-each迴圈疊代集合時修改集合，導致ConcurrentModificationException', 'Remove elements from a collection during a for-each loop: ''for(String item : items) { if(condition) items.remove(item); }''', '在for-each迴圈期間從集合中移除元素：''for(String item : items) { if(condition) items.remove(item); }''', 'medium', '["collections", "iteration", "concurrent-modification"]', '[{"wrong": "for(String item : items) { items.remove(item); }", "correct": "Iterator<String> it = items.iterator(); while(it.hasNext()) { if(condition) it.remove(); }"}]'),

('JS003', 5, 'Ignoring InterruptedException', '忽略InterruptedException', 'Catching InterruptedException without handling it properly, breaking thread interruption mechanism', '捕獲InterruptedException而未適當處理，破壞執行緒中斷機制', 'Catch InterruptedException without rethrowing or setting the interrupt flag: ''try { Thread.sleep(1000); } catch (InterruptedException e) { }''', '捕獲InterruptedException而未重新拋出或設置中斷標誌：''try { Thread.sleep(1000); } catch (InterruptedException e) { }''', 'hard', '["threading", "interruption", "exceptions"]', '[{"wrong": "catch (InterruptedException e) {}", "correct": "catch (InterruptedException e) { Thread.currentThread().interrupt(); }"}]'),

('JS004', 5, 'Boxing/unboxing overhead', '裝箱/拆箱開銷', 'Unnecessary conversions between primitive types and their wrapper classes, impacting performance', '基本型別和其包裝類之間的不必要轉換，影響性能', 'Repeatedly box/unbox in tight loops: ''Integer sum = 0; for(int i=0; i<1000000; i++) { sum += i; }'' instead of using primitive int', '在緊密迴圈中重複裝箱/拆箱：''Integer sum = 0; for(int i=0; i<1000000; i++) { sum += i; }''而非使用基本型別int', 'medium', '["performance", "primitives", "boxing"]', '[{"wrong": "Integer sum = 0; for(int i=0; i<1000000; i++) { sum += i; }", "correct": "int sum = 0; for(int i=0; i<1000000; i++) { sum += i; }"}]'),

('JS005', 5, 'Misuse of finalize()', 'finalize()的誤用', 'Overriding finalize() for resource management, which is unreliable due to garbage collection unpredictability', '覆寫finalize()進行資源管理，由於垃圾收集的不可預測性而不可靠', 'Override finalize() to close resources instead of using try-with-resources or explicit close() calls', '覆寫finalize()來關閉資源而非使用try-with-resources或明確的close()呼叫', 'hard', '["finalize", "resources", "garbage-collection"]', '[{"wrong": "protected void finalize() { resource.close(); }", "correct": "try (Resource resource = new Resource()) { }"}]'),

('JS006', 5, 'Checked exception overuse', '已檢查例外的過度使用', 'Declaring methods to throw checked exceptions that could be handled locally or converted to unchecked exceptions', '宣告方法拋出可以在本地處理或轉換為未檢查例外的已檢查例外', 'Propagate checked exceptions up the call stack when they could be handled or wrapped locally', '當可以在本地處理或包裝時，將已檢查例外向上傳播到呼叫堆疊', 'medium', '["exceptions", "checked", "design"]', '[{"advice": "Use checked exceptions sparingly, prefer unchecked for programming errors"}]'),

('JS007', 5, 'Not using @Override annotation', '未使用@Override註解', 'Omitting @Override annotation when overriding methods, losing compiler validation', '覆寫方法時省略@Override註解，失去編譯器驗證', 'Override methods from superclasses or interfaces without using the @Override annotation', '覆寫超類或介面的方法而未使用@Override註解', 'easy', '["annotations", "override", "validation"]', '[{"wrong": "public String toString() { return name; }", "correct": "@Override public String toString() { return name; }"}]');

-- Insert badges
INSERT INTO badges (badge_id, name_en, name_zh, description_en, description_zh, icon, category, difficulty, points, rarity, criteria) VALUES

-- Achievement Badges (Task Completion)
('first-review', 'First Review', '首次評審', 'Complete your first code review', '完成你的第一次程式碼評審', '🎯', 'achievement', 'easy', 10, 'common', 
 '{"type": "review_count", "threshold": 1, "description": "Complete 1 code review"}'),

('reviewer-novice', 'Reviewer Novice', '評審新手', 'Complete 5 code reviews', '完成5次程式碼評審', '📝', 'achievement', 'easy', 25, 'common',
 '{"type": "review_count", "threshold": 5, "description": "Complete 5 code reviews"}'),

('reviewer-adept', 'Reviewer Adept', '評審能手', 'Complete 25 code reviews', '完成25次程式碼評審', '🎓', 'achievement', 'medium', 100, 'uncommon',
 '{"type": "review_count", "threshold": 25, "description": "Complete 25 code reviews"}'),

('reviewer-master', 'Reviewer Master', '評審大師', 'Complete 50 code reviews', '完成50次程式碼評審', '👑', 'achievement', 'hard', 250, 'rare',
 '{"type": "review_count", "threshold": 50, "description": "Complete 50 code reviews"}'),

('reviewer-legend', 'Reviewer Legend', '評審傳奇', 'Complete 100 code reviews', '完成100次程式碼評審', '🏆', 'achievement', 'legendary', 500, 'legendary',
 '{"type": "review_count", "threshold": 100, "description": "Complete 100 code reviews"}'),

-- Skill-based Badges
('bug-hunter', 'Bug Hunter', '獵蟲者', 'Find all errors in 5 different reviews', '在5次不同評審中找到所有錯誤', '🔍', 'skill', 'medium', 75, 'uncommon',
 '{"type": "perfect_reviews", "threshold": 5, "description": "Achieve 100% accuracy in 5 reviews"}'),

('perfectionist', 'Perfectionist', '完美主義者', 'Achieve 100% accuracy in 3 consecutive reviews', '連續3次評審達到100%準確率', '💎', 'skill', 'hard', 150, 'rare',
 '{"type": "consecutive_perfect", "threshold": 3, "description": "3 consecutive perfect reviews"}'),

('speed-demon', 'Speed Demon', '速度惡魔', 'Complete a review in under 2 minutes with 80%+ accuracy', '在2分鐘內完成評審並達到80%以上準確率', '⚡', 'skill', 'hard', 100, 'rare',
 '{"type": "speed_accuracy", "time_limit": 120, "accuracy_threshold": 80, "description": "Fast and accurate review"}'),

('analytical-mind', 'Analytical Mind', '分析思維', 'Identify errors across all 5 categories in a single session', '在單次會話中識別所有5個類別的錯誤', '🧠', 'skill', 'medium', 80, 'uncommon',
 '{"type": "category_coverage", "threshold": 5, "description": "Identify errors from all categories"}'),

-- Category Mastery Badges
('logic-guru', 'Logic Guru', '邏輯大師', 'Master logical errors with 85%+ accuracy', '以85%以上準確率掌握邏輯錯誤', '🧮', 'skill', 'medium', 60, 'uncommon',
 '{"type": "category_mastery", "category": "Logical", "accuracy": 85, "min_encounters": 10}'),

('syntax-specialist', 'Syntax Specialist', '語法專家', 'Master syntax errors with 85%+ accuracy', '以85%以上準確率掌握語法錯誤', '📐', 'skill', 'easy', 40, 'common',
 '{"type": "category_mastery", "category": "Syntax", "accuracy": 85, "min_encounters": 10}'),

('quality-inspector', 'Quality Inspector', '品質檢查員', 'Master code quality issues with 85%+ accuracy', '以85%以上準確率掌握程式碼品質問題', '🔎', 'skill', 'medium', 60, 'uncommon',
 '{"type": "category_mastery", "category": "Code Quality", "accuracy": 85, "min_encounters": 10}'),

('standards-expert', 'Standards Expert', '標準專家', 'Master standard violations with 85%+ accuracy', '以85%以上準確率掌握標準違規', '📏', 'skill', 'medium', 60, 'uncommon',
 '{"type": "category_mastery", "category": "Standard Violation", "accuracy": 85, "min_encounters": 10}'),

('java-maven', 'Java Maven', 'Java專家', 'Master Java-specific errors with 85%+ accuracy', '以85%以上準確率掌握Java特定錯誤', '☕', 'skill', 'hard', 80, 'rare',
 '{"type": "category_mastery", "category": "Java Specific", "accuracy": 85, "min_encounters": 10}'),

('full-spectrum', 'Full Spectrum', '全光譜', 'Identify at least one error in each category', '在每個類別中至少識別一個錯誤', '🌈', 'skill', 'medium', 100, 'uncommon',
 '{"type": "all_categories", "min_per_category": 1, "description": "Touch all error categories"}'),

-- Consistency Badges
('consistency-champ', 'Consistency Champion', '一致性冠軍', 'Practice for 5 consecutive days', '連續練習5天', '📅', 'consistency', 'easy', 50, 'common',
 '{"type": "consecutive_days", "threshold": 5, "description": "5 day practice streak"}'),

('week-warrior', 'Week Warrior', '週戰士', 'Practice for 7 consecutive days', '連續練習7天', '⚔️', 'consistency', 'medium', 75, 'uncommon',
 '{"type": "consecutive_days", "threshold": 7, "description": "7 day practice streak"}'),

('month-master', 'Month Master', '月度大師', 'Practice for 30 consecutive days', '連續練習30天', '🗓️', 'consistency', 'hard', 200, 'rare',
 '{"type": "consecutive_days", "threshold": 30, "description": "30 day practice streak"}'),

('early-bird', 'Early Bird', '早起鳥', 'Complete 5 reviews before 9 AM', '在上午9點前完成5次評審', '🐦', 'consistency', 'medium', 40, 'uncommon',
 '{"type": "time_based", "hour_threshold": 9, "review_count": 5, "description": "Morning practice sessions"}'),

('night-owl', 'Night Owl', '夜貓子', 'Complete 5 reviews after 10 PM', '在晚上10點後完成5次評審', '🦉', 'consistency', 'medium', 40, 'uncommon',
 '{"type": "time_based", "hour_threshold": 22, "review_count": 5, "description": "Evening practice sessions"}'),

-- Progress Badges
('rising-star', 'Rising Star', '新星', 'Earn 500 points in your first week', '在第一週內獲得500分', '⭐', 'progress', 'medium', 100, 'uncommon',
 '{"type": "points_timeframe", "points": 500, "days": 7, "description": "Fast early progress"}'),

('point-collector', 'Point Collector', '積分收集者', 'Earn 1000 total points', '獲得總計1000分', '💰', 'progress', 'easy', 50, 'common',
 '{"type": "total_points", "threshold": 1000, "description": "Accumulate 1000 points"}'),

('point-master', 'Point Master', '積分大師', 'Earn 5000 total points', '獲得總計5000分', '💎', 'progress', 'medium', 150, 'uncommon',
 '{"type": "total_points", "threshold": 5000, "description": "Accumulate 5000 points"}'),

('progress-tracker', 'Progress Tracker', '進度追蹤者', 'Improve accuracy by 20% over 10 reviews', '在10次評審中將準確率提高20%', '📈', 'progress', 'medium', 80, 'uncommon',
 '{"type": "accuracy_improvement", "improvement": 20, "review_span": 10, "description": "Show consistent improvement"}'),

-- Exploration Badges
('explorer', 'Explorer', '探索者', 'Use the Error Explorer feature 10 times', '使用錯誤探索功能10次', '🗺️', 'achievement', 'easy', 30, 'common',
 '{"type": "feature_usage", "feature": "error_explorer", "threshold": 10, "description": "Explore error library"}'),

('practice-enthusiast', 'Practice Enthusiast', '練習愛好者', 'Complete 10 practice sessions', '完成10次練習會話', '🎯', 'achievement', 'medium', 60, 'common',
 '{"type": "practice_sessions", "threshold": 10, "description": "Complete practice sessions"}'),

('knowledge-seeker', 'Knowledge Seeker', '知識探求者', 'View detailed information for 25 different errors', '查看25個不同錯誤的詳細資訊', '📚', 'achievement', 'medium', 50, 'uncommon',
 '{"type": "error_views", "threshold": 25, "description": "Study error details"}'),

-- Special Event Badges
('beta-tester', 'Beta Tester', 'Beta測試者', 'Participate in the beta testing phase', '參與Beta測試階段', '🧪', 'special', 'medium', 200, 'rare',
 '{"type": "special_event", "event": "beta_testing", "description": "Early system user"}'),

('feedback-provider', 'Feedback Provider', '反饋提供者', 'Provide detailed feedback about the system', '提供關於系統的詳細反饋', '💬', 'special', 'easy', 75, 'uncommon',
 '{"type": "feedback_submission", "min_length": 100, "description": "Helpful system feedback"}'),

('community-helper', 'Community Helper', '社群助手', 'Help other users in the community', '在社群中幫助其他使用者', '🤝', 'special', 'medium', 100, 'uncommon',
 '{"type": "community_action", "actions": 5, "description": "Support fellow learners"}'),

-- Milestone Badges
('century-club', 'Century Club', '百分俱樂部', 'Achieve 100% accuracy in any review', '在任何評審中達到100%準確率', '💯', 'achievement', 'medium', 100, 'uncommon',
 '{"type": "perfect_score", "threshold": 100, "description": "Perfect accuracy achievement"}'),

('marathon-runner', 'Marathon Runner', '馬拉松跑者', 'Spend more than 60 minutes in a single session', '在單次會話中花費超過60分鐘', '🏃', 'achievement', 'medium', 80, 'uncommon',
 '{"type": "session_duration", "minutes": 60, "description": "Extended learning session"}'),

('efficiency-expert', 'Efficiency Expert', '效率專家', 'Maintain 90%+ accuracy with average review time under 5 minutes', '保持90%以上準確率且平均評審時間少於5分鐘', '⚡', 'skill', 'hard', 120, 'rare',
 '{"type": "efficiency", "accuracy": 90, "avg_time": 300, "min_reviews": 10, "description": "Speed and accuracy combined"}');

-- Insert initial streak types
INSERT IGNORE INTO user_streaks (user_id, streak_type) 
SELECT uid, 'daily_practice' FROM users;

INSERT IGNORE INTO user_streaks (user_id, streak_type) 
SELECT uid, 'perfect_reviews' FROM users;

-- =====================================================
-- Badge Prerequisites and Advanced Criteria
-- =====================================================

-- Update badges with prerequisites (some badges require others)
UPDATE badges SET prerequisite_badges = '["reviewer-novice"]' WHERE badge_id = 'reviewer-adept';
UPDATE badges SET prerequisite_badges = '["reviewer-adept"]' WHERE badge_id = 'reviewer-master';
UPDATE badges SET prerequisite_badges = '["reviewer-master"]' WHERE badge_id = 'reviewer-legend';
UPDATE badges SET prerequisite_badges = '["bug-hunter", "perfectionist"]' WHERE badge_id = 'efficiency-expert';
UPDATE badges SET prerequisite_badges = '["logic-guru", "syntax-specialist", "quality-inspector", "standards-expert", "java-maven"]' WHERE badge_id = 'full-spectrum';

