# SheetMind - 智能表格处理工具

## 项目简介

SheetMind 是一个基于 Streamlit 和 DeepSeek API 的智能表格处理工具，能够通过自然语言指令自动生成和执行 pandas 代码，帮助用户快速处理和分析表格数据。

### 主要功能

- **文件上传**：支持 CSV、Excel 文件上传
- **数据预览**：显示表格前 10 行数据和数据形状
- **自然语言指令**：通过自然语言描述数据处理需求
- **AI 代码生成**：使用 DeepSeek API 生成 pandas 代码
- **代码执行**：自动执行生成的代码并显示结果
- **结果下载**：支持下载处理后的 CSV 和 Excel 文件
- **失败日志**：记录执行失败的指令，便于调试
- **使用限制**：每个会话每天最多执行 5 次操作

## 本地运行方法

1. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

2. **配置 API Key**

   在 `.streamlit/secrets.toml` 文件中添加 DeepSeek API Key：

   ```toml
   [default]
   DEEPSEEK_API_KEY = "your_api_key_here"
   ```

3. **启动应用**

   ```bash
   streamlit run app.py
   ```

4. **访问应用**

   打开浏览器，访问 `http://localhost:8501`

## 部署到 Streamlit Cloud

### 步骤 1：准备代码

1. 将代码推送到 GitHub 仓库

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-username/sheetmind.git
   git push -u origin main
   ```

### 步骤 2：在 Streamlit Cloud 上部署

1. 访问 [share.streamlit.io](https://share.streamlit.io/)
2. 点击 "New app"
3. 选择你的 GitHub 仓库
4. 选择分支（通常是 `main`）
5. 设置主文件路径为 `app.py`
6. 点击 "Advanced settings"
7. 在 "Secrets" 部分添加以下内容：

   ```toml
   DEEPSEEK_API_KEY = "your_api_key_here"
   ```

8. 点击 "Deploy"

### 步骤 3：访问部署的应用

部署完成后，Streamlit Cloud 会提供一个 URL，你可以通过该 URL 访问你的应用。

## 注意事项

- 免费用户每天最多执行 5 次操作
- API Key 请妥善保管，不要提交到版本控制系统
- 大文件处理可能会受到 Streamlit Cloud 资源限制
- 如有问题，请查看侧边栏的 "开发者模式" 中的失败日志
