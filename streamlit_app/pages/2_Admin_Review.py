from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from streamlit_app._client import get_json, post_json

st.set_page_config(page_title='人工审核后台', page_icon='✅', layout='wide')
st.title('✅ 人工审核后台')
st.caption('审核老师可以查看检索依据、相关性分数、安全审核结果、快速审核结果，并修改草稿后返回学生。')

status = st.selectbox('状态', ['PENDING_REVIEW', 'APPROVED', 'REJECTED'], index=0)
limit = st.slider('最多加载条数', 10, 100, 50)

if st.button('加载问题列表'):
    try:
        st.session_state['admin_questions'] = get_json('/api/admin/questions', params={'status': status, 'limit': limit}, admin=True)
    except Exception as exc:
        st.error(f'加载失败：{exc}')

questions = st.session_state.get('admin_questions', [])
if not questions:
    st.info('暂无数据，或请点击“加载问题列表”。')
    st.stop()

options = {f"#{q['id']} | {q['risk_level']} | {q['intent']} | {q['raw_question'][:40]}": q for q in questions}
selected_label = st.selectbox('选择问题', list(options.keys()))
q = options[selected_label]

left, right = st.columns([1, 1])
with left:
    st.subheader('问题与流程信息')
    st.write('原始问题：', q['raw_question'])
    st.write('清洗后：', q['cleaned_question'])
    st.write('意图：', q['intent'])
    st.write('相关性分数：', q['relevance_score'])
    st.write('状态：', q['status'])
    st.write('风险等级：', q['risk_level'])
    st.markdown('**输入安全审核**')
    st.json(q['input_safety'])
    st.markdown('**校园本地规则审核**')
    st.json(q['campus_rule'])
    st.markdown('**输出安全审核**')
    st.json(q['output_safety'])

with right:
    st.subheader('检索依据')
    st.markdown('**关键词召回**')
    st.json(q['keyword_hits'])
    st.markdown('**向量召回 + 合并上下文**')
    for i, hit in enumerate(q['context'], start=1):
        with st.expander(f"依据 {i}: {hit.get('doc_title', '')} | score={hit.get('score')}"):
            st.write(hit.get('source_file', ''))
            st.write(hit.get('section_title', ''))
            st.write(hit.get('content', ''))

st.divider()
st.subheader('审核处理')
reviewer = st.text_input('审核人', value='admin')
final_answer = st.text_area('答复内容，可以在草稿基础上修改', value=q.get('draft_answer') or '', height=220)

col1, col2 = st.columns(2)
with col1:
    if st.button('通过并返回学生', type='primary'):
        try:
            resp = post_json(f"/api/admin/questions/{q['id']}/approve", {'reviewer': reviewer, 'final_answer': final_answer}, admin=True)
            st.success(f"已通过：#{resp['id']}")
        except Exception as exc:
            st.error(f'通过失败：{exc}')
with col2:
    reject_reason = st.text_input('拒绝原因', value='知识库依据不足或问题不适合自动答复')
    if st.button('拒绝'):
        try:
            resp = post_json(f"/api/admin/questions/{q['id']}/reject", {'reviewer': reviewer, 'reason': reject_reason}, admin=True)
            st.warning(f"已拒绝：#{resp['id']}")
        except Exception as exc:
            st.error(f'拒绝失败：{exc}')
