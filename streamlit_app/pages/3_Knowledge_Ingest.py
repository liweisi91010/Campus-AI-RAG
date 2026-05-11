from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests
import streamlit as st

from streamlit_app._client import API_BASE, admin_headers, post_json

st.set_page_config(page_title='知识库入库', page_icon='📚', layout='wide')
st.title('📚 Markdown 知识库入库')
st.caption('把学工手册、教务文档的 Markdown 文件上传后，系统会切片、抽关键词、调用 embedding，并写入 MySQL + Milvus。')

st.warning('重建知识库会清空 MySQL 的 knowledge_chunks 表，并重建 Milvus collection。正式环境请先备份。')

uploaded = st.file_uploader('上传 .md 文件，可多选', type=['md'], accept_multiple_files=True)
rebuild = st.checkbox('重建整个知识库', value=False)

if st.button('上传并入库'):
    if not uploaded:
        st.error('请先选择 Markdown 文件。')
    else:
        try:
            files = [('files', (f.name, f.getvalue(), 'text/markdown')) for f in uploaded]
            r = requests.post(
                f'{API_BASE}/api/admin/knowledge/upload-md',
                params={'rebuild': str(rebuild).lower()},
                files=files,
                headers=admin_headers(),
                timeout=600,
            )
            r.raise_for_status()
            st.success('入库完成')
            st.json(r.json())
        except Exception as exc:
            st.error(f'入库失败：{exc}')

st.divider()
st.subheader('服务器目录重建')
st.code('python -m app.ingest_markdown --knowledge-dir ./knowledge --rebuild', language='bash')
if st.button('使用后端 KNOWLEDGE_DIR 重建'):
    try:
        resp = post_json('/api/admin/knowledge/rebuild-from-dir', {}, admin=True, timeout=600)
        st.success('重建完成')
        st.json(resp)
    except Exception as exc:
        st.error(f'重建失败：{exc}')
