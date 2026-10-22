import uuid

import streamlit as st

from src.agent import get_agent
from src.models import Status

st.set_page_config(page_title="المساعد العقاري الذكي", page_icon="🏢", layout="centered")
st.markdown("<style>.stChatMessage, .stMarkdown {direction: rtl; text-align: right;}</style>", unsafe_allow_html=True)

GREETING = ("مرحبًا، أنا مساعد ذكي (AI) لمشروع دليل. يمكنني الإجابة عن الأسعار والتوافر وخطط السداد "
            "والرسوم وحالة الإنشاء، ويمكنك طلب التحدث إلى مندوب مبيعات في أي وقت.")


@st.cache_resource(show_spinner="جاري تحميل النماذج...")
def load_agent():
    return get_agent()


st.title("🏢 المساعد العقاري الذكي")
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]
    st.session_state.session_id = uuid.uuid4().hex

with st.sidebar:
    st.caption("بيانات تجريبية (Synthetic) فقط")
    debug = st.toggle("وضع المطوّر", value=False)
    if st.button("محادثة جديدة"):
        st.session_state.clear()
        st.rerun()
    last = st.session_state.get("last")
    if debug and last:
        st.json(last)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            with st.expander("المصادر"):
                for s in m["sources"]:
                    st.write(f"• {s['title'] or s['doc_id']} — {s['doc_id']} v{s['version']} — {s['issue_date']}")

if prompt := st.chat_input("اسألني هنا... (مثال: كم سعر الوحدة A-019؟)"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("جاري البحث في المصادر المعتمدة..."):
            res = load_agent().ask(prompt, st.session_state.session_id)
        st.markdown(res.reply)
        if res.status is Status.HANDOFF:
            st.info(f"تحويل لمندوب بشري — السبب: {res.reason.value}")
        sources = [{"doc_id": s.doc_id, "title": s.title, "version": s.version, "issue_date": s.issue_date}
                   for s in res.sources]
        if sources:
            with st.expander("المصادر"):
                for s in sources:
                    st.write(f"• {s['title'] or s['doc_id']} — {s['doc_id']} v{s['version']} — {s['issue_date']}")
    st.session_state.last = res.to_dict()
    st.session_state.messages.append({"role": "assistant", "content": res.reply, "sources": sources})
