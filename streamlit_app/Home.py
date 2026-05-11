from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(page_title='校园 AI 客服', page_icon='🎓', layout='centered')

st.title('🎓 校园知识问答系统')
st.caption('学工手册 / 教务文档 RAG + 大模型草稿 + 可选人工审核 / 违禁词快速审核')

st.write('这个入口页模拟“小应用按钮”。学生点击后进入 AI 客服界面；老师或管理员进入审核后台。')

st.page_link('pages/1_Student_QA.py', label='进入学生 AI 客服', icon='💬')
st.page_link('pages/2_Admin_Review.py', label='进入人工审核后台', icon='✅')
st.page_link('pages/3_Knowledge_Ingest.py', label='上传/重建 Markdown 知识库', icon='📚')

st.divider()
st.markdown('''
**当前最小闭环**：学生提问 → 清洗纠错 → 高校关键词库意图识别 → MySQL 关键词召回 → Milvus 向量召回 → 大模型草稿 → 安全与相关性审核 → 人工审核或违禁词快速审核 → 返回学生。
''')
