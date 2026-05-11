from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from streamlit_app._client import get_json, post_json

st.set_page_config(page_title='学生 AI 客服', page_icon='💬', layout='wide')
st.title('💬 学生 AI 客服')
st.caption('如果开启人工审核，学生端只会在审核通过后看到最终答复；如果关闭人工审核，系统会先做违禁词快速审核，通过后直接返回。')

with st.form('ask_form'):
    student_id = st.text_input('学号 / 学生标识', value='20260001')
    question = st.text_area('请输入问题', value='校园卡丢了应该怎么补办？', height=120)
    submitted = st.form_submit_button('提交问题')

if submitted:
    try:
        resp = post_json('/api/questions', {'student_id': student_id, 'question': question}, timeout=180)
        st.success(resp['message'])
        st.info(f"问题编号：{resp['question_id']}｜状态：{resp['status']}｜风险等级：{resp['risk_level']}")
        st.markdown('**本次提交的问题：**')
        st.write(resp.get('raw_question') or question)
        cleaned_question = resp.get('cleaned_question')
        if cleaned_question and cleaned_question != (resp.get('raw_question') or question):
            st.caption(f'清洗后问题：{cleaned_question}')
        st.session_state['last_question_id'] = resp['question_id']
        st.session_state['last_student_id'] = student_id
        st.session_state['last_question_text'] = resp.get('raw_question') or question
    except Exception as exc:
        st.error(f'提交失败：{exc}')

st.divider()
st.subheader('查询审核结果')
col1, col2 = st.columns(2)
with col1:
    qid = st.number_input('问题编号', min_value=1, value=int(st.session_state.get('last_question_id', 1)), step=1)
with col2:
    sid = st.text_input('学号 / 学生标识（用于校验）', value=st.session_state.get('last_student_id', '20260001'))

if st.session_state.get('last_question_text'):
    st.caption(f"最近一次提交的问题：{st.session_state['last_question_text']}")

if st.button('刷新审核结果'):
    try:
        resp = get_json(f'/api/questions/{qid}', params={'student_id': sid})
        st.write(f"状态：**{resp['status']}**")
        st.write(resp['message'])

        st.markdown('**当前问题编号对应的问题：**')
        st.info(resp.get('raw_question') or '后端没有返回问题内容，请更新后端代码并重启 FastAPI。')

        cleaned_question = resp.get('cleaned_question')
        if cleaned_question and cleaned_question != resp.get('raw_question'):
            st.caption(f'清洗后问题：{cleaned_question}')
        if resp.get('created_at'):
            st.caption(f"提交时间：{resp['created_at']}")

        if resp.get('final_answer'):
            st.success(resp['final_answer'])
        if resp.get('review_reason'):
            st.warning(resp['review_reason'])
    except Exception as exc:
        st.error(f'查询失败：{exc}')
