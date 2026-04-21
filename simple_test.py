import pandas as pd

# 测试DataFrame
df = pd.DataFrame({
    '车船号': ['海L90666', '海L12345', '海L90666', '海L78901'],
    '日期': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04'],
    '货物': ['A20013', 'B30024', 'A20013', 'C40035'],
    '数量': [100, 200, 150, 300]
})

# 测试系统提示词构建
user_instruction = "将车船号为海L90666的所有出车记录整理出来"
columns = list(df.columns)
dtypes = df.dtypes.to_dict()
sample_data = df.head(5).to_dict(orient='records')
row_count = len(df)

system_prompt = """你是一个专业的数据处理助手，精通 pandas 库。用户会提供一个 DataFrame（变量名为 df），以及一个自然语言指令。你需要根据指令生成可执行的 Python 代码，对 df 进行操作，并将最终结果赋值给 df。

### 输入信息：
- 用户指令：{user_instruction}
- 列名：{columns}
- 每列数据类型：{dtypes}
- 前5行样例数据（JSON格式）：{sample_data}
- 数据总行数：{row_count}

### 代码要求：
1. 只返回纯 Python 代码，不要有任何解释、注释或额外文本。
2. 代码必须修改 df 变量，使得 df 成为处理后的结果。
3. 可以使用任何 pandas 操作（筛选、分组、聚合、排序、合并、透视、时间处理、字符串处理等）。
4. 如果指令需要多步操作，请生成完整的、可一步执行或顺序执行的代码。
5. 禁止使用危险操作（eval, exec, open, __import__ 等），禁止与文件系统交互。
6. 如果指令无法实现（如缺少必要列），请返回一行注释：# UNSUPPORTED: 原因。

### 处理常见复杂需求的通用策略（内置知识，请参考这些模式生成代码）：

#### 一、筛选与条件过滤
- 单条件筛选：使用 df[df['列名'] == 值]
- 多条件且（&）：使用 df[(df['列名'] > 值) & (df['列名'] == '值')]
- 多条件或（|）：使用 df[(df['列名'] > 值) | (df['列名'] == '值')]
- 反向筛选（不等于）：使用 df[df['列名'] != 值]
- 包含子字符串：使用 df[df['列名'].str.contains('关键词', na=False)]
- 不包含子字符串：使用 df[~df['列名'].str.contains('关键词', na=False)]
- 空值筛选：使用 df[df['列名'].isna()] 或 df[df['列名'].notna()]
- 介于两个值之间：使用 df[df['列名'].between(低值, 高值)]
- 属于某个列表：使用 df[df['列名'].isin([值1, 值2, ...])]

### 输出格式示例：
df = df[df['列名'] == '值']
""".format(
    user_instruction=user_instruction,
    columns=columns,
    dtypes=dtypes,
    sample_data=sample_data,
    row_count=row_count
)

print("系统提示词构建成功！")
print(f"列名: {columns}")
print(f"数据类型: {dtypes}")
print(f"样例数据: {sample_data}")
print(f"数据总行数: {row_count}")

# 测试代码生成逻辑
test_code = "df = df[df['车船号'] == '海L90666']"

# 测试代码执行
local_vars = {"df": df.copy()}
exec(test_code, {}, local_vars)
processed_df = local_vars["df"]

print("\n测试代码执行成功！")
print("处理前数据:")
print(df)
print("\n处理后数据:")
print(processed_df)
