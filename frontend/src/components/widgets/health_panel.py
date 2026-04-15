import streamlit as st
from utils.health_check import run_frontend_checks

_CHECK_LABELS = {
    "postgresql":         "PostgreSQL (logging)",
    "jira_endpoint":      "Jira Endpoint",
    "azure_function_app": "Azure Function App",
}
_DOT = {"ok": "#3fb950", "warn": "#388bfd", "fail": "#a371f7"}


def health_panel():
    if "health_check_results" not in st.session_state:
        st.session_state.health_check_results = run_frontend_checks()

    report  = st.session_state.health_check_results
    overall = report["overall"]
    checks  = report["checks"]

    title = {"ok": "All Systems Operational", "warn": "System Warning", "fail": "System Error"}[overall]

    with st.expander(f"System Status — {title}", expanded=(overall != "ok")):
        st.markdown("""
        <style>
        .sys-row{display:flex;align-items:flex-start;gap:10px;padding:9px 2px;
            border-bottom:1px solid rgba(255,255,255,0.07);}
        .sys-row:last-child{border-bottom:none;}
        .sys-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:5px;}
        .sys-label{font-size:12.5px;font-weight:700;color:#dde1f0;line-height:1.3;}
        .sys-msg{font-size:11px;color:#8892a8;line-height:1.45;margin-top:2px;word-break:break-word;}
        </style>
        """, unsafe_allow_html=True)

        rows = "<div>"
        for key, result in checks.items():
            c = _DOT[result["status"]]
            rows += f"""<div class="sys-row">
                <span class="sys-dot" style="background:{c};box-shadow:0 0 5px {c}80"></span>
                <div style="flex:1;min-width:0">
                    <div class="sys-label">{_CHECK_LABELS.get(key, key)}</div>
                    <div class="sys-msg">{result['message']}</div>
                </div></div>"""
        rows += "</div>"
        st.markdown(rows, unsafe_allow_html=True)

        if st.button("Re-check", key="health_recheck", icon=":material/refresh:"):
            del st.session_state.health_check_results
            st.rerun()
