import streamlit as st
import pandas as pd
import numpy as np
import os
import requests
import json
import threading
from datetime import datetime

# 创建logs文件夹
if not os.path.exists('logs'):
    os.makedirs('logs')

# 失败日志文件路径
FAILURE_LOG_FILE = 'logs/failure_logs.jsonl'

# 记录失败日志的函数
def log_failure(user_instruction, filename=None, columns=None, row_count=None, generated_code=None, error_type=None, error_message=None, retry_used=False):
    """记录失败日志到JSON Lines文件"""
    # 构建日志条目
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_instruction': user_instruction,
        'filename': filename,
        'columns': columns,
        'row_count': row_count,
        'generated_code': generated_code,
        'error_type': error_type,
        'error_message': error_message,
        'retry_used': retry_used
    }
    
    # 异步写入日志，避免阻塞主流程
    def write_log():
        try:
            with open(FAILURE_LOG_FILE, 'a', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            # 记录写入日志时的错误，但不影响主流程
            try:
                print(f"写入失败日志时出错: {type(e).__name__}: {e}")
            except Exception as ex:
                print(f"写入失败日志时出错: 未知错误: {type(ex).__name__}: {ex}")
    
    # 启动线程写入日志
    threading.Thread(target=write_log).start()

# 设置页面标题和布局
st.set_page_config(
    page_title="SheetMind",
    page_icon="📊",
    layout="wide"
)

# 检查并初始化session_state
if 'tables' not in st.session_state:
    st.session_state.tables = {}
if 'table_order' not in st.session_state:
    st.session_state.table_order = []
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()  # 用于跟踪已处理的文件
if 'current_table' not in st.session_state:
    st.session_state.current_table = None
if 'executions' not in st.session_state:
    st.session_state.executions = 0
if 'last_reset' not in st.session_state:
    st.session_state.last_reset = datetime.now().date()
if 'vip' not in st.session_state:
    st.session_state.vip = False
if 'developer_mode' not in st.session_state:
    st.session_state.developer_mode = False

# 检查是否需要重置执行次数
current_date = datetime.now().date()
if st.session_state.last_reset != current_date:
    st.session_state.executions = 0
    st.session_state.last_reset = current_date

# 添加自定义CSS样式
st.markdown("""
<style>
    /* 整体样式 */
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        width: 300px;
        min-width: 300px;
        max-width: 300px;
    }
    
    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        background-color: #0f52ba;
        color: white;
        border: none;
        padding: 8px 16px;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background-color: #1e65b8;
    }
    
    /* 表格列表项样式 */
    .table-item {
        padding: 8px 12px;
        border-radius: 8px;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .table-item:hover {
        background-color: #f0f2f6;
    }
    
    .table-item.selected {
        background-color: #e6f0ff;
        border-left: 4px solid #0f52ba;
    }
    
    /* 分隔线样式 */
    .divider {
        height: 1px;
        background-color: #e0e0e0;
        margin: 16px 0;
    }
    
    /* 卡片样式 */
    .card {
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        padding: 16px;
        margin-bottom: 16px;
        background-color: white;
    }
    
    /* 状态提示样式 */
    .status {
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 页面标题
st.title("SheetMind - 智能表格处理工具")

# 侧边栏

# 设置折叠面板
with st.sidebar.expander("设置"):
    # 开发者密码
    dev_password = st.secrets.get("DEV_PASSWORD", "")
    entered_password = st.text_input("开发者密码", type="password")
    if dev_password:
        if entered_password == dev_password:
            st.session_state.developer_mode = True
            st.session_state.vip = True  # 开发者密码自动获得VIP
            st.success("开发者模式已启用（无限次数）")
            
            # 开发者工具
            if st.button("查看失败日志"):
                st.subheader("失败指令记录")
                try:
                    if os.path.exists(FAILURE_LOG_FILE):
                        # 读取日志文件
                        logs = []
                        with open(FAILURE_LOG_FILE, 'r', encoding='utf-8') as f:
                            for line in f:
                                try:
                                    log = json.loads(line.strip())
                                    logs.append(log)
                                except:
                                    pass
                        
                        # 按时间倒序排序
                        logs.sort(key=lambda x: x['timestamp'], reverse=True)
                        
                        # 显示日志表格
                        if logs:
                            st.dataframe(logs)
                        else:
                            st.info("暂无失败日志")
                    else:
                        st.info("暂无失败日志")
                except Exception as e:
                    try:
                        st.error(f"读取日志失败: {type(e).__name__}: {e}")
                    except Exception as ex:
                        st.error(f"读取日志失败: 未知错误: {type(ex).__name__}: {ex}")
            
            if st.button("清空日志"):
                if st.checkbox("确认清空所有日志", False):
                    try:
                        if os.path.exists(FAILURE_LOG_FILE):
                            os.remove(FAILURE_LOG_FILE)
                        st.success("日志已清空")
                    except Exception as e:
                        try:
                            st.error(f"清空日志失败: {type(e).__name__}: {e}")
                        except Exception as ex:
                            st.error(f"清空日志失败: 未知错误: {type(ex).__name__}: {ex}")
        elif entered_password:
            st.session_state.developer_mode = False
            st.warning("密码错误，请重新输入")
        else:
            st.session_state.developer_mode = False
    else:
        st.session_state.developer_mode = False
        if entered_password:
            st.info("开发者密码未配置，请联系管理员")

# VIP模式折叠面板
with st.sidebar.expander("VIP 模式"):
    vip_codes = st.secrets.get("VIP_CODE", "").split(",")
    vip_code = st.text_input("VIP 邀请码")
    if vip_codes[0]:
        if vip_code in vip_codes:
            st.session_state.vip = True
            st.success("VIP 模式已启用：无限次数")
        elif vip_code:
            st.session_state.vip = False
            st.warning("邀请码错误，请重新输入")
        # 否则保持当前状态
    else:
        if vip_code:
            st.info("VIP 邀请码未配置，请联系管理员")

    # 清除 VIP 按钮
    if st.session_state.vip:
        if st.button("清除 VIP"):
            st.session_state.vip = False
            st.info("已退出 VIP 模式")

# 分隔线
st.sidebar.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# 帮助文本
st.sidebar.markdown("<p style='font-size: 12px;'>**指令示例：** 删除空行、将订单表和产品表根据产品ID左连接</p>", unsafe_allow_html=True)

# 从st.secrets读取API Key
try:
    deepseek_api_key = st.secrets["DEEPSEEK_API_KEY"]
except KeyError:
    # 直接显示错误，让用户填写API key
    st.error("⚠️ 未找到 API Key，请在 .streamlit/secrets.toml 中配置 DEEPSEEK_API_KEY")
    deepseek_api_key = None

# 主功能区

# 1. 表格管理区域
st.subheader("表格管理")

# 上传文件
uploaded_files = st.file_uploader(
    "上传文件（支持多个）",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)

# 处理上传的文件
if uploaded_files:
    # 清空现有表和顺序，因为file_uploader会返回所有已上传的文件
    st.session_state.tables = {}
    st.session_state.table_order = []
    
    # 遍历所有文件
    for uploaded_file in uploaded_files:
        try:
            # 生成基础表名
            base_name = uploaded_file.name.rsplit('.', 1)[0]
            table_name = base_name
            counter = 1
            
            # 生成唯一表名
            while table_name in st.session_state.tables:
                table_name = f"{base_name}_{counter}"
                counter += 1
            
            # 读取文件
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
                df = pd.read_excel(uploaded_file)
            
            # 保存到tables字典
            st.session_state.tables[table_name] = df
            # 更新表格顺序
            st.session_state.table_order.append(table_name)
            
            # 设置当前表为最后上传的表
            st.session_state.current_table = table_name
        except Exception as e:
            try:
                st.error(f"读取文件 {uploaded_file.name} 时出错: {type(e).__name__}: {e}")
            except Exception as ex:
                st.error(f"读取文件 {uploaded_file.name} 时出错: 未知错误: {type(ex).__name__}: {ex}")
else:
    # 当没有文件时，清空tables和table_order
    st.session_state.tables = {}
    st.session_state.table_order = []
    st.session_state.current_table = None



# 显示当前表信息
if st.session_state.tables:
    # 确保current_table存在且有效
    if not st.session_state.current_table or st.session_state.current_table not in st.session_state.tables:
        if st.session_state.table_order:
            # 按上传顺序找到最后一个存在的表
            for table_name in reversed(st.session_state.table_order):
                if table_name in st.session_state.tables:
                    st.session_state.current_table = table_name
                    break
    
    if st.session_state.current_table:
        # 使用下拉框选择当前表
        # 按上传顺序显示表格选项
        table_options = [table for table in st.session_state.table_order if table in st.session_state.tables]
        selected_table = st.selectbox(
            "当前表",
            table_options,
            index=table_options.index(st.session_state.current_table) if st.session_state.current_table in table_options else 0
        )
        if selected_table != st.session_state.current_table:
            st.session_state.current_table = selected_table

# 2. 数据预览区域
if st.session_state.tables and st.session_state.current_table:
    st.subheader("数据预览")
    current_df = st.session_state.tables[st.session_state.current_table]
    if not current_df.empty:
        st.dataframe(current_df.head(10))
    else:
        st.info("当前表为空，请上传文件")
else:
    st.info("暂无表格，请上传文件")

# 3. 指令输入与执行区域
if st.session_state.tables and st.session_state.current_table:
    st.subheader("指令输入")
    user_instruction = st.text_area(
        "请输入对表格的操作指令",
        placeholder="例如: 删除所有空行、将'年龄'列乘以2、将 销售表 和 产品表 根据 产品ID 左连接",
        height=100
    )
    

    
    # 执行按钮
    if st.button("执行", disabled=not (st.session_state.current_table and user_instruction and deepseek_api_key) or (not st.session_state.vip and st.session_state.executions >= 5)):
        # 检查执行次数
        if not st.session_state.vip and st.session_state.executions >= 5:
            st.error("免费用户每天最多执行5次操作，请升级账户以获得更多次数。")
        else:
            with st.status("正在处理...", expanded=True) as status:
                # 增加执行次数（非VIP用户）
                if not st.session_state.vip:
                    st.session_state.executions += 1
                
                # 步骤1: 生成代码
                status.update(label="正在分析指令...")
                try:
                    # 收集所有表的元数据
                    tables_metadata = []
                    for table_name, df in st.session_state.tables.items():
                        table_info = {
                            "表名": table_name,
                            "列名": list(df.columns) if not df.empty else [],
                            "数据类型": df.dtypes.to_dict() if not df.empty else {},
                            "前2行样例": df.head(2).to_dict(orient='records') if not df.empty else [],
                            "数据总行数": len(df)
                        }
                        tables_metadata.append(table_info)
                    
                    # 构建系统提示词
                    system_prompt = """你是一个专业的数据处理助手，精通 pandas 库。用户会提供多个 DataFrame（存储在 st.session_state['tables'] 字典中，键为表名，值为 DataFrame），以及一个自然语言指令。你需要根据指令生成可执行的 Python 代码，对这些表进行操作。

### 输入信息：
- 用户指令：{user_instruction}
- 所有表的元数据：{tables_metadata}

### 代码要求：
1. **思维链（Chain of Thought）**：在输出代码之前，先用注释输出“任务拆解步骤”，例如：
   # 步骤1：从 session_state 中读取表 A 和表 B
   # 步骤2：根据订单号列进行内连接
   # 步骤3：将结果存入新表 'merged_table'
   然后再输出实际代码。

2. **多表操作规范**：
   - 从 st.session_state['tables'] 中读取指定表，例如：df1 = st.session_state['tables']['表名1']
   - 引用列名时，必须使用 `表名['列名']` 格式，避免歧义
   - 如果指令涉及多表关联，必须显式写出连接条件（例如 `pd.merge(df1, df2, left_on='A', right_on='B', how='inner')`）

3. **表关联推理辅助**：
   - 如果用户没有明确指定关联列，应根据列名相似度（如“订单ID” vs “ID”）或常见模式（如“产品编号”）进行合理推断
   - 在代码注释中说明推断依据
   - 如果无法推断，返回错误提示：“无法确定表 A 和表 B 的关联列，请指定（如：将 A 的‘用户ID’与 B 的‘ID’关联）”

4. **新表命名规范**：
   - 如果用户指令没有指定新表名，自动生成形如 `表A_表B_操作_序号` 的名称（如 `orders_products_join_1`）
   - 代码中必须检查新表名是否已存在，若存在则自动加后缀

5. **错误处理与用户提示**：
   - 生成的代码应包含 try-except 块，捕获 KeyError（列名不存在）、ValueError（类型不匹配）等常见异常
   - 通过 st.error 给出友好提示
   - 如果筛选/连接后结果为空，通过 st.warning 提示“操作后结果为空，请检查关联条件”

6. **性能提示**：
   - 如果用户尝试连接的两个表都超过 10000 行，在代码注释中建议用户先筛选再连接

7. **其他要求**：
   - 操作后可以将结果存回原表或创建新表
   - 可以使用任何 pandas 操作（筛选、分组、聚合、排序、合并、透视、时间处理、字符串处理等）
   - 如果指令需要多步操作，生成完整的、可一步执行或顺序执行的代码
   - 禁止使用危险操作（eval, exec, open, __import__ 等），禁止与文件系统交互
   - 如果指令无法实现（如缺少必要列），返回一行注释：# UNSUPPORTED: 原因

### 输出格式示例：
# 步骤1：从 session_state 中读取销售表
# 步骤2：筛选车船号为海L90666的记录
# 步骤3：将结果存回销售表
df = st.session_state['tables']['销售表']
try:
    df = df[df['车船号'] == '海L90666']
    if df.empty:
        st.warning("操作后结果为空，请检查筛选条件")
    st.session_state['tables']['销售表'] = df
except KeyError as e:
    st.error(f"列名不存在: {str(e)}")
except Exception as e:
    st.error(f"操作失败: {str(e)}")

# 步骤1：从 session_state 中读取销售表和产品表
# 步骤2：根据产品ID列进行左连接
# 步骤3：将结果存入新表 '销售明细'
df1 = st.session_state['tables']['销售表']
df2 = st.session_state['tables']['产品表']
try:
    df_merged = df1.merge(df2, on='产品ID', how='left')
    if df_merged.empty:
        st.warning("操作后结果为空，请检查关联条件")
    # 检查新表名是否已存在
    new_table_name = '销售明细'
    counter = 1
    while new_table_name in st.session_state['tables']:
        new_table_name = f'销售明细_{counter}'
        counter += 1
    st.session_state['tables'][new_table_name] = df_merged
except KeyError as e:
    st.error(f"列名不存在: {str(e)}")
except Exception as e:
    st.error(f"操作失败: {str(e)}")
""".format(
                            user_instruction=user_instruction,
                            tables_metadata=tables_metadata
                        )
                        
                    # 调试模式下打印完整prompt
                    if st.session_state.developer_mode:
                        st.write("\n=== 调试信息：完整Prompt ===")
                        st.text(system_prompt)
                    
                    # 调用DeepSeek API生成代码
                    try:
                        response = requests.post(
                            "https://api.deepseek.com/v1/chat/completions",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {deepseek_api_key}"
                            },
                            json={
                                "model": "deepseek-chat",
                                "messages": [
                                    {
                                        "role": "system",
                                        "content": system_prompt
                                    },
                                    {
                                        "role": "user",
                                        "content": user_instruction
                                    }
                                ],
                                "temperature": 0.1
                            }
                        )
                        
                        # 检查响应状态码
                        if response.status_code != 200:
                            raise Exception(f"API调用失败，状态码: {response.status_code}")
                        
                        # 尝试解析JSON响应
                        try:
                            result = response.json()
                        except Exception as ex:
                            raise Exception(f"解析API响应失败: {ex}")
                        
                        # 检查响应格式
                        if 'choices' not in result:
                            raise Exception(f"API响应格式错误: 缺少'choices'字段")
                        if not result['choices']:
                            raise Exception(f"API响应格式错误: 'choices'字段为空")
                        if 'message' not in result['choices'][0]:
                            raise Exception(f"API响应格式错误: 缺少'message'字段")
                        if 'content' not in result['choices'][0]['message']:
                            raise Exception(f"API响应格式错误: 缺少'content'字段")
                        
                        generated_code = result['choices'][0]['message']['content']
                    except Exception as ex:
                        # 重新抛出异常，让外层的错误处理代码捕获
                        raise Exception(f"API调用失败: {ex}")
                    
                    status.update(label="正在执行代码...")
                    
                    # 步骤2: 执行代码
                    try:
                        # 创建一个安全的执行环境
                        local_vars = {"st": st, "pd": pd, "np": np}
                        exec(generated_code, {}, local_vars)
                        
                        status.update(label="处理完成", state="complete")
                        
                        # 检查是否有新表被创建
                        new_tables = set(st.session_state.tables.keys()) - set(local_vars.get('original_tables', st.session_state.tables.keys()))
                        if new_tables:
                            st.success(f"已创建新表: {', '.join(new_tables)}")
                        
                        # 4. 执行结果与下载区域
                        st.subheader("执行结果")
                        current_df = st.session_state.tables[st.session_state.current_table]
                        if not current_df.empty:
                            st.dataframe(current_df.head(10))
                            st.write(f"处理后数据形状: {current_df.shape[0]} 行 × {current_df.shape[1]} 列")
                        else:
                            st.info("当前表为空")
                        
                        # 下载选项
                        st.subheader("下载选项")
                        
                        # 下载当前表
                        @st.cache_data
                        def convert_df(df):
                            return df.to_csv(index=False).encode('utf-8')
                        
                        csv = convert_df(current_df)
                        st.download_button(
                            label="✅ 下载当前表 (CSV)",
                            data=csv,
                            file_name=f"{st.session_state.current_table}.csv",
                            mime="text/csv"
                        )
                        
                        # 也提供Excel下载
                        @st.cache_data
                        def convert_to_excel(df):
                            import io
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                df.to_excel(writer, index=False)
                            return output.getvalue()
                        
                        excel = convert_to_excel(current_df)
                        st.download_button(
                            label="✅ 下载当前表 (Excel)",
                            data=excel,
                            file_name=f"{st.session_state.current_table}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        # 重新操作按钮
                        if st.button("🔄 重新操作"):
                            st.experimental_rerun()
                            
                    except Exception as e:
                        # 错误处理 - 重试一次
                        status.update(label="执行出错，正在尝试修复...")
                        
                        # 安全地获取错误信息，避免str(e)可能的问题
                        try:
                            error_message = f"{type(e).__name__}: {e}"
                        except Exception as ex:
                            error_message = f"未知错误: {type(ex).__name__}: {ex}"
                        # 显示详细的错误信息
                        st.error(f"代码执行错误: {error_message}")
                        
                        # 记录代码执行失败日志（第一次失败）
                        log_failure(
                            user_instruction=user_instruction,
                            columns=[table['列名'] for table in tables_metadata],
                            row_count=[table['数据总行数'] for table in tables_metadata],
                            generated_code=generated_code if 'generated_code' in locals() else None,
                            error_type="代码执行错误",
                            error_message=error_message,
                            retry_used=False
                        )
                        # 构建系统提示词（重试时）
                        retry_system_prompt = """你是一个专业的数据处理助手，精通 pandas 库。用户会提供多个 DataFrame（存储在 st.session_state['tables'] 字典中，键为表名，值为 DataFrame），以及一个自然语言指令。你需要根据指令生成可执行的 Python 代码，对这些表进行操作。

### 输入信息：
- 用户指令：{user_instruction}
- 所有表的元数据：{tables_metadata}
- 执行错误：{error_message}

### 代码要求：
1. **思维链（Chain of Thought）**：在输出代码之前，先用注释输出“任务拆解步骤”，例如：
   # 步骤1：从 session_state 中读取表 A 和表 B
   # 步骤2：根据订单号列进行内连接
   # 步骤3：将结果存入新表 'merged_table'
   然后再输出实际代码。

2. **多表操作规范**：
   - 从 st.session_state['tables'] 中读取指定表，例如：df1 = st.session_state['tables']['表名1']
   - 引用列名时，必须使用 `表名['列名']` 格式，避免歧义
   - 如果指令涉及多表关联，必须显式写出连接条件（例如 `pd.merge(df1, df2, left_on='A', right_on='B', how='inner')`）

3. **表关联推理辅助**：
   - 如果用户没有明确指定关联列，应根据列名相似度（如“订单ID” vs “ID”）或常见模式（如“产品编号”）进行合理推断
   - 在代码注释中说明推断依据
   - 如果无法推断，返回错误提示：“无法确定表 A 和表 B 的关联列，请指定（如：将 A 的‘用户ID’与 B 的‘ID’关联）”

4. **新表命名规范**：
   - 如果用户指令没有指定新表名，自动生成形如 `表A_表B_操作_序号` 的名称（如 `orders_products_join_1`）
   - 代码中必须检查新表名是否已存在，若存在则自动加后缀

5. **错误处理与用户提示**：
   - 生成的代码应包含 try-except 块，捕获 KeyError（列名不存在）、ValueError（类型不匹配）等常见异常
   - 通过 st.error 给出友好提示
   - 如果筛选/连接后结果为空，通过 st.warning 提示“操作后结果为空，请检查关联条件”

6. **性能提示**：
   - 如果用户尝试连接的两个表都超过 10000 行，在代码注释中建议用户先筛选再连接

7. **其他要求**：
   - 操作后可以将结果存回原表或创建新表
   - 可以使用任何 pandas 操作（筛选、分组、聚合、排序、合并、透视、时间处理、字符串处理等）
   - 如果指令需要多步操作，生成完整的、可一步执行或顺序执行的代码
   - 禁止使用危险操作（eval, exec, open, __import__ 等），禁止与文件系统交互
   - 如果指令无法实现（如缺少必要列），返回一行注释：# UNSUPPORTED: 原因

### 输出格式示例：
# 步骤1：从 session_state 中读取销售表
# 步骤2：筛选车船号为海L90666的记录
# 步骤3：将结果存回销售表
df = st.session_state['tables']['销售表']
try:
    df = df[df['车船号'] == '海L90666']
    if df.empty:
        st.warning("操作后结果为空，请检查筛选条件")
    st.session_state['tables']['销售表'] = df
except KeyError as e:
    st.error(f"列名不存在: {str(e)}")
except Exception as e:
    st.error(f"操作失败: {str(e)}")

# 步骤1：从 session_state 中读取销售表和产品表
# 步骤2：根据产品ID列进行左连接
# 步骤3：将结果存入新表 '销售明细'
df1 = st.session_state['tables']['销售表']
df2 = st.session_state['tables']['产品表']
try:
    df_merged = df1.merge(df2, on='产品ID', how='left')
    if df_merged.empty:
        st.warning("操作后结果为空，请检查关联条件")
    # 检查新表名是否已存在
    new_table_name = '销售明细'
    counter = 1
    while new_table_name in st.session_state['tables']:
        new_table_name = f'销售明细_{counter}'
        counter += 1
    st.session_state['tables'][new_table_name] = df_merged
except KeyError as e:
    st.error(f"列名不存在: {str(e)}")
except Exception as e:
    st.error(f"操作失败: {str(e)}")
""".format(
                            user_instruction=user_instruction,
                            tables_metadata=tables_metadata,
                            error_message=error_message
                        )
                        
                        # 再次调用API修复代码
                        response = requests.post(
                            "https://api.deepseek.com/v1/chat/completions",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {deepseek_api_key}"
                            },
                            json={
                                "model": "deepseek-chat",
                                "messages": [
                                    {
                                        "role": "system",
                                        "content": retry_system_prompt
                                    },
                                    {
                                        "role": "user",
                                        "content": f"{user_instruction}\n\n执行错误：{error_message}"
                                    }
                                ],
                                "temperature": 0.1
                            }
                        )
                        
                        result = response.json()
                        fixed_code = result['choices'][0]['message']['content']
                        
                        try:
                            # 执行修复后的代码
                            local_vars = {"st": st, "pd": pd, "np": np}
                            exec(fixed_code, {}, local_vars)
                            
                            status.update(label="修复成功，处理完成", state="complete")
                            
                            # 检查是否有新表被创建
                            new_tables = set(st.session_state.tables.keys()) - set(local_vars.get('original_tables', st.session_state.tables.keys()))
                            if new_tables:
                                st.success(f"已创建新表: {', '.join(new_tables)}")
                            
                            # 4. 执行结果与下载区域
                            st.subheader("执行结果")
                            current_df = st.session_state.tables[st.session_state.current_table]
                            if not current_df.empty:
                                st.dataframe(current_df.head(10))
                                st.write(f"处理后数据形状: {current_df.shape[0]} 行 × {current_df.shape[1]} 列")
                            else:
                                st.info("当前表为空")
                            
                            # 下载选项
                            st.subheader("下载选项")
                            
                            # 下载当前表
                            @st.cache_data
                            def convert_df(df):
                                return df.to_csv(index=False).encode('utf-8')
                            
                            csv = convert_df(current_df)
                            st.download_button(
                                label="✅ 下载当前表 (CSV)",
                                data=csv,
                                file_name=f"{st.session_state.current_table}.csv",
                                mime="text/csv"
                            )
                            
                            # 也提供Excel下载
                            @st.cache_data
                            def convert_to_excel(df):
                                import io
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    df.to_excel(writer, index=False)
                                return output.getvalue()
                            
                            excel = convert_to_excel(current_df)
                            st.download_button(
                                label="✅ 下载当前表 (Excel)",
                                data=excel,
                                file_name=f"{st.session_state.current_table}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                            # 重新操作按钮
                            if st.button("🔄 重新操作", key="retry2"):
                                st.experimental_rerun()
                                
                        except Exception as e2:
                            status.update(label="执行失败", state="error")
                            # 安全地获取错误信息，避免str(e)可能的问题
                            try:
                                error_message2 = f"{type(e2).__name__}: {e2}"
                            except Exception as ex:
                                error_message2 = f"未知错误: {type(ex).__name__}: {ex}"
                            st.error(f"代码执行失败: {error_message2}")
                            
                            # 记录代码执行失败日志（重试后仍然失败）
                            log_failure(
                                user_instruction=user_instruction,
                                columns=[table['列名'] for table in tables_metadata],
                                row_count=[table['数据总行数'] for table in tables_metadata],
                                generated_code=fixed_code if 'fixed_code' in locals() else None,
                                error_type="代码执行错误（重试后）",
                                error_message=error_message2,
                                retry_used=True
                            )
                except Exception as e:
                    status.update(label="API调用失败", state="error")
                    # 尝试获取更详细的错误信息
                    error_detail = "API调用失败"
                    try:
                        # 使用简单的字符串，避免处理异常对象可能的问题
                        error_detail = "API调用失败"
                    except:
                        error_detail = "API调用失败"
                    try:
                        if hasattr(e, 'response') and e.response:
                            try:
                                error_detail += "\n响应状态码: " + str(e.response.status_code)
                            except:
                                error_detail += "\n获取状态码失败"
                            try:
                                error_json = e.response.json()
                                error_detail += "\n错误信息: API响应错误"
                                # 检查是否是余额不足的错误
                                try:
                                    if error_json.get('error', {}).get('message') == 'Insufficient Balance':
                                        st.error("API Key余额不足，请更换有效的API Key或充值。")
                                        status.update(label="API Key余额不足", state="error")
                                except:
                                    pass
                            except:
                                error_detail += "\n获取响应JSON失败"
                    except:
                        error_detail += "\n获取详细信息失败"
                    st.error("调用DeepSeek API时出错: " + error_detail)
                    
                    # 记录API调用失败日志
                    try:
                        log_failure(
                            user_instruction=user_instruction,
                            columns=[table['列名'] for table in tables_metadata],
                            row_count=[table['数据总行数'] for table in tables_metadata],
                            error_type="API错误",
                            error_message=error_detail,
                            retry_used=False
                        )
                    except:
                        # 记录日志失败时，不影响主流程
                        pass

# 底部信息
if st.session_state.vip:
    st.markdown("---\nVIP 模式：无限次数")
else:
    st.markdown(f"---\n执行次数: {st.session_state.executions}/5 (每天重置)")
