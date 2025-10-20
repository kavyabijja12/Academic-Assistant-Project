# RAG_UI.py
import streamlit as st
from dotenv import load_dotenv
from RAGChat import RAGChat

# Initialize environment
load_dotenv()

@st.cache_resource(show_spinner=False)
def init_rag():
    rag = RAGChat(use_cohere=False)   # set True if you have Cohere API key
    success = rag.load_index()
    return rag if success else None

def main():
    st.set_page_config(page_title="🎓 ASU Academic Assistant", page_icon="🎓", layout="wide")
    st.title("🎓 ASU Polytechnic – Academic Assistant")
    st.markdown("Ask questions about Information Technology courses, electives, and program details.")

    rag = init_rag()
    if not rag:
        st.error("Failed to load vector index. Please check your setup.")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("📚 Sources"):
                    for i, d in enumerate(msg["sources"], 1):
                        snippet = d.page_content[:400] + ("..." if len(d.page_content) > 400 else "")
                        st.write(f"**Source {i}:** {snippet}")
                        st.divider()

    if prompt := st.chat_input("Ask something about ASU IT program..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching ASU IT materials..."):
                try:
                    answer, docs = rag.ask(prompt)
                    st.markdown(answer)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "sources": docs}
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

    # Sidebar
    with st.sidebar:
        st.header("System Info")
        info = rag.get_info()
        st.success("✅ RAG System Loaded")
        st.write(f"**Model:** {info.get('model', 'Unknown')}")
        st.write(f"**Vector Store:** {info.get('vector_store', 'N/A')}")
        st.write(f"**Chunks:** {info.get('chunks', 0)}")
        st.write(f"**Retriever:** {info.get('retriever', 'Hybrid Search')}")


        st.divider()
        st.header("💡 Example Questions")
        examples = [
            "What are the core IT courses?",
            "Tell me about the capstone project.",
            "What are the graduation requirements?"
        ]
        for q in examples:
            if st.button(q, key=q):
                st.session_state.messages.append({"role": "user", "content": q})
                st.rerun()

        st.divider()
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages.clear()
            st.rerun()

if __name__ == "__main__":
    main()
