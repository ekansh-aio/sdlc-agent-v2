"""
Landing page — shown before the user makes an auth decision.
Two CTAs: Connect to Jira (opens login dialog) · Continue without Jira.
"""
import os
import streamlit as st
from theme import load_theme, landing_gradient
from components.dialogs.jira_login import jira_login_dialog

JIRA_ENDPOINT = os.getenv("JIRA_ENDPOINT", "")


def render(jira):
    load_theme()
    # Clear any stale sidebar-collapsed state from localStorage
    st.html("""<script>
    (function(){
        Object.keys(localStorage).forEach(function(k){
            if(k.toLowerCase().includes('sidebar')||k.toLowerCase().includes('collapsed'))
                localStorage.removeItem(k);
        });
    })();
    </script>""")

    if "show_jira_login" not in st.session_state:
        st.session_state.show_jira_login = False

    jira_configured = bool(JIRA_ENDPOINT)
    jira_label      = JIRA_ENDPOINT.rstrip("/") if jira_configured else "not configured"
    dot_color       = "#3fb950" if jira_configured else "#6e7681"

    # ── Hide chrome ──
    st.markdown("""
    <style>
    [data-testid="stSidebar"],[data-testid="stToolbar"],
    [data-testid="stDecoration"],footer,#MainMenu{display:none!important}
    </style>
    """, unsafe_allow_html=True)

    landing_gradient()

    # ── Top nav ──
    st.markdown(f"""
    <div style="
        background:linear-gradient(110deg,#0d1117 0%,#0f1f3d 45%,#161b22 100%);
        border-bottom:1px solid rgba(56,139,253,0.35);
        padding:0 40px;height:58px;
        display:flex;align-items:center;justify-content:space-between;
        margin:-1rem -1rem 0;
    ">
        <div style="display:flex;align-items:center;gap:12px;">
            <svg width="32" height="32" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg"
                 style="filter:drop-shadow(0 2px 8px rgba(56,139,253,0.45))">
              <defs>
                <linearGradient id="nav-body" x1="0" y1="0" x2="34" y2="34" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stop-color="#1a2744"/>
                  <stop offset="100%" stop-color="#1e1435"/>
                </linearGradient>
                <linearGradient id="nav-glow" x1="0" y1="0" x2="34" y2="34" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stop-color="#388bfd"/>
                  <stop offset="100%" stop-color="#a371f7"/>
                </linearGradient>
              </defs>
              <rect x="5" y="9" width="24" height="20" rx="5" fill="url(#nav-body)" stroke="url(#nav-glow)" stroke-width="1.4"/>
              <line x1="17" y1="9" x2="17" y2="4" stroke="#388bfd" stroke-width="1.5" stroke-linecap="round"/>
              <circle cx="17" cy="3.5" r="1.8" fill="#388bfd"/>
              <rect x="9" y="15" width="5" height="4" rx="1.5" fill="#388bfd" opacity="0.9"/>
              <rect x="20" y="15" width="5" height="4" rx="1.5" fill="#a371f7" opacity="0.9"/>
              <circle cx="11" cy="16.5" r="0.9" fill="#79c0ff"/>
              <circle cx="22" cy="16.5" r="0.9" fill="#d2a8ff"/>
              <path d="M11.5 23.5 Q17 27 22.5 23.5" stroke="#58a6ff" stroke-width="1.4" stroke-linecap="round" fill="none"/>
              <rect x="2" y="15" width="3" height="6" rx="1.5" fill="url(#nav-body)" stroke="url(#nav-glow)" stroke-width="1.2"/>
              <rect x="29" y="15" width="3" height="6" rx="1.5" fill="url(#nav-body)" stroke="url(#nav-glow)" stroke-width="1.2"/>
            </svg>
            <span style="color:#e6edf3;font-size:14px;font-weight:600;letter-spacing:0.2px;">
                AI Helpers for Quality Engineering
            </span>
        </div>
        <span style="display:inline-flex;align-items:center;gap:6px;
            font-size:11px;color:#6e7681;background:#161b22;
            border:1px solid rgba(255,255,255,0.07);border-radius:6px;padding:4px 10px;
            font-family:'Cascadia Code','Consolas',monospace;">
            <span style="width:6px;height:6px;border-radius:50%;
                background:{dot_color};display:inline-block;"></span>
            Jira &middot; {jira_label}
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)

    # ── Two-column hero ──
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        .ey{display:inline-flex;align-items:center;gap:8px;
            background:rgba(56,139,253,0.1);border:1px solid rgba(56,139,253,0.28);
            border-radius:100px;padding:4px 14px 4px 10px;
            font-size:11px;color:#79c0ff;font-weight:600;
            letter-spacing:.05em;text-transform:uppercase;margin-bottom:24px;}
        .ey .edot{width:6px;height:6px;border-radius:50%;background:#388bfd;
            animation:epulse 2s ease-out infinite;}
        @keyframes epulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.8)}}
        @media(prefers-reduced-motion:reduce){.ey .edot{animation:none}}
        .lh1{font-family:'Plus Jakarta Sans',system-ui,sans-serif;
            font-size:clamp(28px,3.5vw,46px);font-weight:800;
            line-height:1.1;letter-spacing:-0.03em;color:#e6edf3;margin:0 0 18px;}
        .lg{background:linear-gradient(135deg,#388bfd 0%,#a371f7 55%,#79c0ff 100%);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
        .lsub{font-size:14.5px;color:#8b949e;line-height:1.75;margin-bottom:28px;}
        .lsub strong{color:#e6edf3;font-weight:600;}
        .pills{display:grid;grid-template-columns:repeat(3,auto);justify-content:start;gap:7px;margin-bottom:28px;}
        .pill{display:inline-flex;align-items:center;gap:6px;
            background:#161b22;border:1px solid rgba(255,255,255,0.07);
            border-radius:6px;padding:4px 11px;font-size:11.5px;color:#8b949e;
            font-weight:500;font-family:'Cascadia Code','Consolas',monospace;white-space:nowrap;}
        .pill svg{width:12px;height:12px;stroke:currentColor;fill:none;
            stroke-width:2;stroke-linecap:round;stroke-linejoin:round;}
        .chips{display:flex;align-items:center;gap:14px;flex-wrap:nowrap;margin-bottom:28px;}
        .chip{display:flex;align-items:center;gap:6px;font-size:11px;color:#6e7681;
            font-family:'Cascadia Code','Consolas',monospace;}
        .cdot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
        </style>

        <div class="ey"><span class="edot"></span>Quality Engineering &middot; SDLC Agents</div>
        <div class="lh1">Automate QE.<br>Ship <span class="lg">tested code</span><br>faster.</div>
        <p class="lsub">
            A <strong>multi-agent AI pipeline</strong> that turns rough requirements into
            structured Jira stories and <strong>manual + BDD test cases</strong>
            &mdash; ready to push, no copy-paste.
        </p>
        <div class="pills">
            <span class="pill"><svg viewBox="0 0 24 24"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>Requirement Analysis</span>
            <span class="pill"><svg viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>Test Case Generation</span>
            <span class="pill"><svg viewBox="0 0 24 24"><path d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>Jira Integration</span>
            <span class="pill"><svg viewBox="0 0 24 24"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>Azure Functions</span>
            <span class="pill"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>GPT-4o</span>
        </div>
        <div class="chips">
            <div class="chip"><span class="cdot" style="background:#388bfd;box-shadow:0 0 5px rgba(56,139,253,.5)"></span>Azure OpenAI</div>
            <div class="chip"><span class="cdot" style="background:#a371f7;box-shadow:0 0 5px rgba(163,113,247,.5)"></span>Azure Functions</div>
            <div class="chip"><span class="cdot" style="background:#3fb950;box-shadow:0 0 5px rgba(63,185,80,.5)"></span>PostgreSQL</div>
        </div>
        """, unsafe_allow_html=True)

        # ── CTAs ──
        st.markdown("""
        <style>
        /* Equalise both CTA buttons to the same height */
        [data-testid="stHorizontalBlock"]:has([data-testid="stBaseButton-primary"])
          [data-testid^="stBaseButton"] button {
            height: 46px !important;
            min-height: 46px !important;
            padding: 0 20px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        /* Jira button — teal accent */
        #cta-jira-marker ~ div [data-testid="stBaseButton-primary"] button,
        #cta-jira-marker + div [data-testid="stBaseButton-primary"] button {
            background: linear-gradient(135deg,#1f8a70 0%,#12b886 100%) !important;
            border: none !important;
            color: #ffffff !important;
            box-shadow: 0 2px 10px rgba(18,184,134,0.28) !important;
        }
        #cta-jira-marker ~ div [data-testid="stBaseButton-primary"] button:hover,
        #cta-jira-marker + div [data-testid="stBaseButton-primary"] button:hover {
            background: linear-gradient(135deg,#2aa88a 0%,#20c997 100%) !important;
            box-shadow: 0 4px 18px rgba(18,184,134,0.40) !important;
        }
        </style>
        <span id="cta-jira-marker" style="display:none"></span>
        """, unsafe_allow_html=True)
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("Connect to Jira", use_container_width=True,
                         type="primary", key="cta_jira"):
                st.session_state.show_jira_login = True
                st.rerun()
        with c2:
            if st.button("Continue without Jira", use_container_width=True,
                         key="cta_skip"):
                st.session_state.jira_user_authenticated  = False
                st.session_state.jira_auth_popup_actioned = True
                st.rerun()

    with right:
        st.markdown("""
        <style>
        .term{background:#161b22;border:1px solid rgba(255,255,255,0.07);
            border-radius:10px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.55);
            font-family:'Cascadia Code','Consolas',monospace;font-size:12px;margin-bottom:14px;}
        .tbar{display:flex;align-items:center;gap:6px;
            background:#21262d;border-bottom:1px solid rgba(255,255,255,0.07);padding:8px 14px;}
        .tb{width:10px;height:10px;border-radius:50%;}
        .tbody{padding:14px 18px;line-height:1.8;color:#e6edf3;}
        .t-pr{color:#3fb950}.t-ag{color:#a371f7;font-weight:600}
        .t-ok{color:#3fb950}.t-info{color:#79c0ff}.t-dim{color:#6e7681}
        .t-out{color:#a371f7}.t-warn{color:#58a6ff}
        .t-typing{display:inline-block;overflow:hidden;white-space:nowrap;
            border-right:2px solid #388bfd;vertical-align:bottom;
            animation:typing 2.4s steps(40,end) forwards,blink .75s step-end infinite;}
        @keyframes typing{from{width:0}to{width:100%}}
        @keyframes blink{0%,100%{border-color:#388bfd}50%{border-color:transparent}}
        @media(prefers-reduced-motion:reduce){.t-typing{animation:none;width:100%;border-right:none}}
        .aflow{background:#161b22;border:1px solid rgba(255,255,255,0.07);
            border-radius:10px;padding:14px 18px;}
        .af-label{font-size:10px;color:#6e7681;text-transform:uppercase;letter-spacing:.08em;
            margin-bottom:10px;font-family:'Cascadia Code','Consolas',monospace;}
        .af-nodes{display:flex;align-items:center;}
        .af-node{display:flex;flex-direction:column;align-items:center;gap:4px;flex:1;}
        .af-icon{width:36px;height:36px;border-radius:8px;display:flex;
            align-items:center;justify-content:center;border:1px solid rgba(255,255,255,0.07);}
        .af-icon svg{width:16px;height:16px;stroke:currentColor;fill:none;
            stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round;}
        .ib{background:rgba(56,139,253,.15);border-color:rgba(56,139,253,.3);color:#388bfd;}
        .ip{background:rgba(163,113,247,.15);border-color:rgba(163,113,247,.3);color:#a371f7;}
        .iy{background:rgba(56,139,253,.12);border-color:rgba(56,139,253,.3);color:#388bfd;}
        .ig{background:rgba(63,185,80,.15);border-color:rgba(63,185,80,.3);color:#3fb950;}
        .af-name{font-size:9px;color:#8b949e;text-align:center;
            font-family:'Cascadia Code','Consolas',monospace;white-space:nowrap;}
        .af-arr{color:rgba(255,255,255,0.13);font-size:16px;margin:0 2px 16px;user-select:none;}
        </style>
        <div class="term">
            <div class="tbar">
                <span class="tb" style="background:rgba(255,255,255,0.12)"></span>
                <span class="tb" style="background:rgba(255,255,255,0.12)"></span>
                <span class="tb" style="background:rgba(255,255,255,0.12)"></span>
                <span style="margin-left:8px;font-size:11px;color:#6e7681">agent &middot; pipeline &middot; stdout</span>
            </div>
            <div class="tbody">
                <div><span class="t-pr">$</span> <span class="t-typing">sdlc-agents run --helper RAS --input "user login"</span></div>
                <div style="margin-top:6px"><span class="t-dim">&#9658; Starting multi-agent pipeline...</span></div>
                <div><span class="t-ag">[AnalyserAgent] </span><span class="t-info">drafting user story (INVEST check)</span></div>
                <div><span class="t-ag">[ReviewerAgent] </span><span class="t-ok">&#10003; PASS &middot; forwarding</span></div>
                <div><span class="t-ag">[FinalResponse] </span><span class="t-out">story compiled &middot; TERMINATE</span></div>
                <div style="margin-top:6px"><span class="t-dim">&#8212;&#8212;&#8212;&#8212;&#8212;&#8212;&#8212;&#8212;&#8212;</span></div>
                <div><span class="t-ok">&#10003;</span> <span style="color:#e6edf3">Title:</span> <span class="t-out">Secure auth via OAuth 2.0</span></div>
                <div><span class="t-ok">&#10003;</span> <span style="color:#e6edf3">AC:</span> <span class="t-out">3 scenarios &middot; Given/When/Then</span></div>
                <div style="margin-top:6px"><span class="t-dim">&#9658; Pushing AIHQE-42... </span><span class="t-ok">204 OK</span></div>
            </div>
        </div>
        <div class="aflow">
            <div class="af-label">Agent execution chain</div>
            <div class="af-nodes">
                <div class="af-node">
                    <div class="af-icon ib"><svg viewBox="0 0 24 24"><path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg></div>
                    <div class="af-name">Request<br>Handler</div>
                </div>
                <div class="af-arr">&#8594;</div>
                <div class="af-node">
                    <div class="af-icon ip"><svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h7"/></svg></div>
                    <div class="af-name">Analyser<br>Agent</div>
                </div>
                <div class="af-arr">&#8594;</div>
                <div class="af-node">
                    <div class="af-icon iy"><svg viewBox="0 0 24 24"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg></div>
                    <div class="af-name">Reviewer<br>Agent</div>
                </div>
                <div class="af-arr">&#8594;</div>
                <div class="af-node">
                    <div class="af-icon ig"><svg viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></div>
                    <div class="af-name">Final<br>Response</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.show_jira_login:
        jira_login_dialog(jira)
