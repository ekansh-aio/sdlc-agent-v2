import streamlit as st


def clipboard_button(escaped_response: str):
    st.html(f"""
    <style>
        .copy-btn{{
            display:inline-flex;align-items:center;gap:6px;
            background:rgba(255,255,255,0.05);
            border:1px solid rgba(56,139,253,0.40);
            border-radius:8px;padding:6px 14px;
            font-size:12.5px;font-weight:600;
            font-family:'Segoe UI',system-ui,sans-serif;
            color:#8b949e;cursor:pointer;
            transition:all 0.2s cubic-bezier(0.4,0,0.2,1);white-space:nowrap;
        }}
        .copy-btn:hover{{background:#388bfd;border-color:#388bfd;color:#fff;
            box-shadow:0 4px 14px rgba(56,139,253,0.38);transform:translateY(-1px)}}
        .copy-btn:active{{transform:translateY(0);box-shadow:none}}
        .copy-btn.copied{{background:rgba(63,185,80,0.15);border-color:rgba(63,185,80,0.40);color:#3fb950}}
    </style>
    <button class="copy-btn" id="copyBtn" onclick="copyText()">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
        </svg>Copy
    </button>
    <script>
    const SVG_COPY='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>';
    const SVG_CHECK='<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
    function copyText(){{
        const btn=document.getElementById('copyBtn');
        navigator.clipboard.writeText({escaped_response}).then(()=>{{
            btn.classList.add('copied');btn.innerHTML=SVG_CHECK+' Copied!';
            setTimeout(()=>{{btn.classList.remove('copied');btn.innerHTML=SVG_COPY+'Copy';}},2000);
        }},()=>{{btn.innerHTML='Failed';}});
    }}
    </script>
    """)
