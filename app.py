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
            print(f"写入失败日志时出错: {str(e)}")
    
    # 启动线程写入日志
    threading.Thread(target=write_log).start()

# 设置页面标题和布局
st.set_page_config(
    page_title="SheetMind",
    page_icon="📊",
    layout="wide"
)

# 检查并初始化session_state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'processed_df' not in st.session_state:
    st.session_state.processed_df = None
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

# 页面标题
st.title("SheetMind - 智能表格处理工具")

# 侧边栏

# 设置 expander
with st.sidebar.expander("设置"):
    # 从st.secrets读取API Key
    try:
        deepseek_api_key = st.secrets["DEEPSEEK_API_KEY"]
    except KeyError:
        st.error("⚠️ 未找到 API Key，请在 .streamlit/secrets.toml 中配置 DEEPSEEK_API_KEY")
        deepseek_api_key = None
    
    # 开发者模式（仅限管理员可见）
    dev_password = st.secrets.get("DEV_PASSWORD", "")
    entered_password = st.text_input("开发者密码", type="password")
    if dev_password:
        if entered_password == dev_password:
            st.session_state.developer_mode = True
            st.success("开发者模式已启用")
        elif entered_password:
            st.session_state.developer_mode = False
            st.warning("密码错误，请重新输入")
        else:
            st.session_state.developer_mode = False
    else:
        st.session_state.developer_mode = False
        if entered_password:
            st.info("开发者密码未配置，请联系管理员")

# VIP 模式 expander
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
        else:
            st.session_state.vip = False
    else:
        st.session_state.vip = False
        if vip_code:
            st.info("VIP 邀请码未配置，请联系管理员")
    
    # 清除 VIP 按钮
    if st.session_state.vip:
        if st.button("清除 VIP"):
            st.session_state.vip = False
            st.info("已退出 VIP 模式")

# 开发者模式功能
if st.session_state.developer_mode:
    st.sidebar.subheader("开发者工具")
    
    # 查看失败日志
    if st.sidebar.button("查看失败日志"):
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
            st.error(f"读取日志失败: {str(e)}")
    
    # 清空日志
    if st.sidebar.button("清空日志"):
        if st.sidebar.checkbox("确认清空所有日志", False):
            try:
                if os.path.exists(FAILURE_LOG_FILE):
                    os.remove(FAILURE_LOG_FILE)
                st.sidebar.success("日志已清空")
            except Exception as e:
                st.sidebar.error(f"清空日志失败: {str(e)}")

# 主功能区
col1, col2 = st.columns(2)

with col1:
    # 1. 文件上传
    st.header("1. 文件上传")
    uploaded_file = st.file_uploader(
        "选择要上传的文件",
        type=["csv", "xlsx", "xls"]
    )
    
    # 2. 数据读取与预览
    if uploaded_file is not None:
        try:
            with st.status("正在读取文件...", expanded=True) as status:
                # 根据文件类型读取
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
                    df = pd.read_excel(uploaded_file)
                
                st.session_state.df = df
                status.update(label="文件读取成功", state="complete")
                
            # 显示数据预览
            st.subheader("数据预览")
            st.dataframe(df.head(10))
            st.write(f"数据形状: {df.shape[0]} 行 × {df.shape[1]} 列")
            
        except Exception as e:
            st.error(f"读取文件时出错: {str(e)}")

with col2:
    # 3. 指令输入
    st.header("2. 指令输入")
    user_instruction = st.text_area(
        "请输入对表格的操作指令",
        placeholder="例如: 删除所有空行、将'年龄'列乘以2",
        height=100
    )
    
    # 4. AI代码生成与执行
    if st.button("执行", disabled=not (uploaded_file and user_instruction and deepseek_api_key) or (not st.session_state.vip and st.session_state.executions >= 5)):
        # 检查执行次数
        if not st.session_state.vip and st.session_state.executions >= 5:
            st.error("免费用户每天最多执行5次操作，请升级账户以获得更多次数。")
        else:
            # 检查df是否存在
            if st.session_state.df is None:
                st.error("请先上传文件并确保文件被正确读取")
            else:
                with st.status("正在处理...", expanded=True) as status:
                    # 增加执行次数（非VIP用户）
                    if not st.session_state.vip:
                        st.session_state.executions += 1
                    
                    # 步骤1: 生成代码
                    status.update(label="正在分析指令...")
                    try:
                        # 收集DataFrame信息
                        df_info = st.session_state.df
                        columns = list(df_info.columns)
                        dtypes = df_info.dtypes.to_dict()
                        sample_data = df_info.head(5).to_dict(orient='records')
                        row_count = len(df_info)
                        
                        # 构建系统提示词
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
3. 你可以使用任何 pandas 操作（筛选、分组、聚合、排序、合并、透视、时间处理、字符串处理等）。
4. 如果指令需要多步操作，请生成完整的、可一步执行或顺序执行的代码。
5. 禁止使用危险操作（eval, exec, open, __import__ 等），禁止与文件系统交互。
6. 如果指令无法实现（如缺少必要列），请返回一行注释：# UNSUPPORTED: 原因。

### 输出格式示例：
df = df[df['车船号'] == '海L90666']
""".format(
                            user_instruction=user_instruction,
                            columns=columns,
                            dtypes=dtypes,
                            sample_data=sample_data,
                            row_count=row_count
                        )
                        
                        # 调试模式下打印完整prompt
                        if developer_mode:
                            st.write("\n=== 调试信息：完整Prompt ===")
                            st.text(system_prompt)
                        
                        # 调用DeepSeek API生成代码
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
                        
                        result = response.json()
                        generated_code = result['choices'][0]['message']['content']
                        
                        status.update(label="正在执行代码...")
                        
                        # 步骤2: 执行代码
                        try:
                            # 创建一个安全的执行环境
                            local_vars = {"df": st.session_state.df.copy()}
                            exec(generated_code, {}, local_vars)
                            processed_df = local_vars["df"]
                            
                            # 保存处理后的数据
                            st.session_state.processed_df = processed_df
                            
                            status.update(label="处理完成", state="complete")
                            
                            # 安全机制：检查筛选结果
                            if processed_df.shape[0] == 0:
                                # 检查用户指令是否包含筛选关键词
                                filter_keywords = ['筛选', '过滤', '选择', '查找', '为', '等于', '是']
                                if any(keyword in user_instruction for keyword in filter_keywords):
                                    st.warning("筛选结果为空，请检查列名或筛选条件是否正确。")
                                    
                                    # 记录结果为空的失败日志
                                    log_failure(
                                        user_instruction=user_instruction,
                                        filename=uploaded_file.name if uploaded_file else None,
                                        columns=columns if 'columns' in locals() else None,
                                        row_count=row_count if 'row_count' in locals() else None,
                                        generated_code=generated_code if 'generated_code' in locals() else None,
                                        error_type="结果为空",
                                        error_message="筛选结果为空，请检查列名或筛选条件是否正确",
                                        retry_used=False
                                    )
                            
                            # 显示处理结果
                            st.subheader("处理结果预览")
                            st.dataframe(processed_df.head(10))
                            st.write(f"处理后数据形状: {processed_df.shape[0]} 行 × {processed_df.shape[1]} 列")
                            
                            # 6. 预览与确认
                            st.subheader("操作选项")
                            
                            # 直接显示下载按钮
                            @st.cache_data
                            def convert_df(df):
                                return df.to_csv(index=False).encode('utf-8')
                            
                            csv = convert_df(processed_df)
                            st.download_button(
                                label="✅ 下载CSV文件",
                                data=csv,
                                file_name="processed_data.csv",
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
                            
                            excel = convert_to_excel(processed_df)
                            st.download_button(
                                label="✅ 下载Excel文件",
                                data=excel,
                                file_name="processed_data.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            
                            # 重新操作按钮
                            if st.button("🔄 重新操作"):
                                st.session_state.processed_df = None
                                st.experimental_rerun()
                                
                        except Exception as e:
                            # 错误处理 - 重试一次
                            status.update(label="执行出错，正在尝试修复...")
                            
                            error_message = str(e)
                            # 显示详细的错误信息
                            st.error(f"代码执行错误: {error_message}")
                            
                            # 记录代码执行失败日志（第一次失败）
                            log_failure(
                                user_instruction=user_instruction,
                                filename=uploaded_file.name if uploaded_file else None,
                                columns=columns if 'columns' in locals() else None,
                                row_count=row_count if 'row_count' in locals() else None,
                                generated_code=generated_code if 'generated_code' in locals() else None,
                                error_type="代码执行错误",
                                error_message=error_message,
                                retry_used=False
                            )
                            # 构建系统提示词（重试时）
                            retry_system_prompt = """你是一个专业的数据处理助手，精通 pandas 库。用户会提供一个 DataFrame（变量名为 df），以及一个自然语言指令。你需要根据指令生成可执行的 Python 代码，对 df 进行操作，并将最终结果赋值给 df。

### 输入信息：
- 用户指令：{user_instruction}
- 列名：{columns}
- 每列数据类型：{dtypes}
- 前5行样例数据（JSON格式）：{sample_data}
- 数据总行数：{row_count}
- 执行错误：{error_message}

### 代码要求：
1. 只返回纯 Python 代码，不要有任何解释、注释或额外文本。
2. 代码必须修改 df 变量，使得 df 成为处理后的结果。
3. 你可以使用任何 pandas 操作（筛选、分组、聚合、排序、合并、透视、时间处理、字符串处理等）。
4. 如果指令需要多步操作，请生成完整的、可一步执行或顺序执行的代码。
5. 禁止使用危险操作（eval, exec, open, __import__ 等），禁止与文件系统交互。
6. 如果指令无法实现（如缺少必要列），请返回一行注释：# UNSUPPORTED: 原因。

### 输出格式示例：
df = df[df['车船号'] == '海L90666']
""".format(
                                user_instruction=user_instruction,
                                columns=columns,
                                dtypes=dtypes,
                                sample_data=sample_data,
                                row_count=row_count,
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
                                local_vars = {"df": st.session_state.df.copy()}
                                exec(fixed_code, {}, local_vars)
                                processed_df = local_vars["df"]
                                
                                # 保存处理后的数据
                                st.session_state.processed_df = processed_df
                                
                                status.update(label="修复成功，处理完成", state="complete")
                                
                                # 显示处理结果
                                st.subheader("处理结果预览")
                                st.dataframe(processed_df.head(10))
                                st.write(f"处理后数据形状: {processed_df.shape[0]} 行 × {processed_df.shape[1]} 列")
                                
                                # 6. 预览与确认
                                st.subheader("操作选项")
                                
                                # 直接显示下载按钮
                                @st.cache_data
                                def convert_df(df):
                                    return df.to_csv(index=False).encode('utf-8')
                                
                                csv = convert_df(processed_df)
                                st.download_button(
                                    label="✅ 下载CSV文件",
                                    data=csv,
                                    file_name="processed_data.csv",
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
                                
                                excel = convert_to_excel(processed_df)
                                st.download_button(
                                    label="✅ 下载Excel文件",
                                    data=excel,
                                    file_name="processed_data.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                                
                                # 重新操作按钮
                                if st.button("🔄 重新操作", key="retry2"):
                                    st.session_state.processed_df = None
                                    st.experimental_rerun()
                                    
                            except Exception as e2:
                                status.update(label="执行失败", state="error")
                                st.error(f"代码执行失败: {str(e2)}")
                                
                                # 记录代码执行失败日志（重试后仍然失败）
                                log_failure(
                                    user_instruction=user_instruction,
                                    filename=uploaded_file.name if uploaded_file else None,
                                    columns=columns if 'columns' in locals() else None,
                                    row_count=row_count if 'row_count' in locals() else None,
                                    generated_code=fixed_code if 'fixed_code' in locals() else None,
                                    error_type="代码执行错误（重试后）",
                                    error_message=str(e2),
                                    retry_used=True
                                )
                    except Exception as e:
                        status.update(label="API调用失败", state="error")
                        # 尝试获取更详细的错误信息
                        error_detail = str(e)
                        try:
                            if hasattr(e, 'response') and e.response:
                                error_detail += f"\n响应状态码: {e.response.status_code}"
                                try:
                                    error_json = e.response.json()
                                    error_detail += f"\n错误信息: {error_json}"
                                    # 检查是否是余额不足的错误
                                    if error_json.get('error', {}).get('message') == 'Insufficient Balance':
                                        st.error("API Key余额不足，请更换有效的API Key或充值。")
                                        status.update(label="API Key余额不足", state="error")
                                except:
                                    pass
                        except:
                            pass
                        st.error(f"调用DeepSeek API时出错: {error_detail}")
                        
                        # 记录API调用失败日志
                        log_failure(
                            user_instruction=user_instruction,
                            filename=uploaded_file.name if uploaded_file else None,
                            columns=columns if 'columns' in locals() else None,
                            row_count=row_count if 'row_count' in locals() else None,
                            error_type="API错误",
                            error_message=error_detail,
                            retry_used=False
                        )

# 底部信息
if st.session_state.vip:
    st.markdown("---\nVIP 模式：无限次数")
else:
    st.markdown(f"---\n执行次数: {st.session_state.executions}/5 (每天重置)")
