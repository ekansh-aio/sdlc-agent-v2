import streamlit as st

# Clear Streamlit's sidebar collapsed state from localStorage so it can never
# get permanently stuck closed. Runs on every page load — harmless if already open.
_SIDEBAR_RESET_JS = """
<script>
(function() {
    var keys = Object.keys(localStorage);
    keys.forEach(function(k) {
        if (k.toLowerCase().includes('sidebar') || k.toLowerCase().includes('collapsed')) {
            localStorage.removeItem(k);
        }
    });
})();
</script>
"""

# Robot mascot SVG — friendly AI bot face in blue/purple palette
_MASCOT_SVG = """
<svg width="34" height="34" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="m-body" x1="0" y1="0" x2="34" y2="34" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#1a2744"/>
      <stop offset="100%" stop-color="#1e1435"/>
    </linearGradient>
    <linearGradient id="m-glow" x1="0" y1="0" x2="34" y2="34" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#388bfd"/>
      <stop offset="100%" stop-color="#a371f7"/>
    </linearGradient>
  </defs>
  <!-- Body / head rounded rect -->
  <rect x="5" y="9" width="24" height="20" rx="5" fill="url(#m-body)" stroke="url(#m-glow)" stroke-width="1.4"/>
  <!-- Antenna -->
  <line x1="17" y1="9" x2="17" y2="4" stroke="#388bfd" stroke-width="1.5" stroke-linecap="round"/>
  <circle cx="17" cy="3.5" r="1.8" fill="#388bfd"/>
  <!-- Eyes — left blue, right purple -->
  <rect x="9" y="15" width="5" height="4" rx="1.5" fill="#388bfd" opacity="0.9"/>
  <rect x="20" y="15" width="5" height="4" rx="1.5" fill="#a371f7" opacity="0.9"/>
  <!-- Eye shine dots -->
  <circle cx="11" cy="16.5" r="0.9" fill="#79c0ff"/>
  <circle cx="22" cy="16.5" r="0.9" fill="#d2a8ff"/>
  <!-- Smile -->
  <path d="M11.5 23.5 Q17 27 22.5 23.5" stroke="#58a6ff" stroke-width="1.4" stroke-linecap="round" fill="none"/>
  <!-- Ear studs -->
  <rect x="2" y="15" width="3" height="6" rx="1.5" fill="url(#m-body)" stroke="url(#m-glow)" stroke-width="1.2"/>
  <rect x="29" y="15" width="3" height="6" rx="1.5" fill="url(#m-body)" stroke="url(#m-glow)" stroke-width="1.2"/>
</svg>"""


def app_header():
    st.html(_SIDEBAR_RESET_JS)
    st.markdown(f"""
    <div class="custom-title">
        <div style="width:34px;height:34px;flex-shrink:0;filter:drop-shadow(0 2px 8px rgba(56,139,253,0.45));">
            {_MASCOT_SVG}
        </div>
        <h3>AI Helpers for Quality Engineering</h3>
    </div>
    """, unsafe_allow_html=True)
