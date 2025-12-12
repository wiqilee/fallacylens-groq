import os
import sys
import io
import html  # for escaping Excerpt / Explanation / Suggestion text

# Make sure we can import the local `fallacylens` package
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import streamlit as st
import streamlit.components.v1 as components  # ✅ ADDED (for typing animation JS)
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from fallacylens.detector import FallacyDetector
from fallacylens.models import FallacySpan
from fallacylens.taxonomy import FALLACY_DEFINITIONS


# ===========================
# PAGE CONFIG
# ===========================
st.set_page_config(
    page_title="FallacyLens · Logical fallacy, bias, and persuasion analyzer",
    layout="wide",
)


# ===========================
# GLOBAL STYLES
# ===========================
st.markdown(
    """
    <style>
    /* Overall background + typography */
    .main {
        position: relative;
        background:
            radial-gradient(circle at top, #191f2a 0, #05070b 45%, #020308 100%);
        color: #f5f5f7;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
        overflow-x: hidden;
    }

    /* Animated UFO layer */
    @keyframes ufoFly {
        0% {
            transform: translate3d(-25vw, -8vh, 0) scale(0.85);
            opacity: 0;
        }
        10% {
            opacity: 0.9;
        }
        50% {
            transform: translate3d(35vw, 6vh, 0) scale(1.05);
            opacity: 1;
        }
        90% {
            opacity: 0.9;
        }
        100% {
            transform: translate3d(115vw, -10vh, 0) scale(0.9);
            opacity: 0;
        }
    }

    @keyframes ufoBeamPulse {
        0% {
            opacity: 0;
            transform: translate3d(5vw, 4vh, 0) scaleX(0.7) scaleY(0.2);
        }
        15% {
            opacity: 0.75;
        }
        50% {
            opacity: 0.4;
            transform: translate3d(35vw, 18vh, 0) scaleX(1.0) scaleY(1.0);
        }
        85% {
            opacity: 0.75;
        }
        100% {
            opacity: 0;
            transform: translate3d(115vw, 6vh, 0) scaleX(0.6) scaleY(0.2);
        }
    }

    .main::before {
        /* UFO disc */
        content: "";
        position: fixed;
        top: 8vh;
        left: -25vw;
        width: 260px;
        height: 120px;
        background:
            radial-gradient(ellipse at 50% 20%, rgba(255,255,255,0.95) 0, rgba(255,255,255,0) 55%),
            radial-gradient(ellipse at 50% 70%, rgba(0,255,200,0.9) 0, rgba(0,255,150,0.0) 65%),
            radial-gradient(ellipse at 50% 50%, #4a4b6e 0, #191a30 45%, rgba(9,11,25,0) 70%);
        border-radius: 50%;
        filter: drop-shadow(0 0 30px rgba(0, 255, 200, 0.9));
        opacity: 0.85;
        animation: ufoFly 22s linear infinite;
        z-index: 0;
        pointer-events: none;
    }

    .main::after {
        /* UFO beam */
        content: "";
        position: fixed;
        top: 14vh;
        left: -15vw;
        width: 320px;
        height: 420px;
        background:
            radial-gradient(circle at 50% 0%, rgba(255,255,255,0.8) 0, rgba(255,255,255,0) 40%),
            radial-gradient(circle at 30% 30%, rgba(0,255,200,0.4) 0, rgba(0,255,200,0) 60%),
            radial-gradient(circle at 70% 50%, rgba(0,255,150,0.4) 0, rgba(0,255,150,0) 65%);
        opacity: 0;
        mix-blend-mode: screen;
        filter: blur(2px);
        animation: ufoBeamPulse 22s linear infinite;
        z-index: 0;
        pointer-events: none;
    }

    /* Layout */
    .block-container {
        padding-top: 2.8rem;
        padding-bottom: 4rem;
        max-width: 1180px;
        margin: 0 auto;
        position: relative;
        z-index: 1; /* above UFO */
    }

    @keyframes softGlow {
        0%   { box-shadow: 0 0 0 rgba(0,0,0,0); }
        50%  { box-shadow: 0 0 22px rgba(88, 166, 255, 0.35); }
        100% { box-shadow: 0 0 0 rgba(0,0,0,0); }
    }

    /* Breathing neon glow for hero header */
    @keyframes headerGlow {
        0% {
            box-shadow:
                0 0 0 rgba(129, 212, 250, 0.0),
                0 0 0 rgba(255, 105, 180, 0.0);
            border-color: rgba(129, 212, 250, 0.55);
        }
        50% {
            box-shadow:
                0 0 26px rgba(129, 212, 250, 0.55),
                0 0 52px rgba(255, 105, 180, 0.22);
            border-color: rgba(129, 212, 250, 0.95);
        }
        100% {
            box-shadow:
                0 0 0 rgba(129, 212, 250, 0.0),
                0 0 0 rgba(255, 105, 180, 0.0);
            border-color: rgba(129, 212, 250, 0.55);
        }
    }

    /* Typing glow animation for text areas */
    @keyframes typingBlink {
        0% {
            box-shadow: 0 0 0px rgba(129,212,250,0.0);
            border-color: rgba(255,255,255,0.9);
        }
        50% {
            box-shadow: 0 0 26px rgba(129,212,250,0.95);
            border-color: rgba(129,212,250,1);
        }
        100% {
            box-shadow: 0 0 0px rgba(129,212,250,0.0);
            border-color: rgba(255,255,255,0.9);
        }
    }

    /* ✅ Premium typing pulse (only while actively typing) */
    @keyframes typingPulsePremium {
        0% {
            border-color: rgba(255,255,255,0.85);
            box-shadow: 0 0 14px rgba(255,255,255,0.30);
        }
        45% {
            border-color: rgba(129,212,250,1);
            box-shadow:
                0 0 22px rgba(129,212,250,0.70),
                0 0 44px rgba(255,105,180,0.22);
        }
        100% {
            border-color: rgba(255,255,255,0.85);
            box-shadow: 0 0 14px rgba(255,255,255,0.30);
        }
    }

    /* Global green pulse for buttons on hover */
    @keyframes greenPulse {
        0%   { box-shadow: 0 0 0 rgba(0,230,118,0.0); }
        50%  { box-shadow: 0 0 26px rgba(0,230,118,0.95); }
        100% { box-shadow: 0 0 0 rgba(0,230,118,0.0); }
    }

    .big-title {
        font-size: 2.7rem;
        font-weight: 800;
        letter-spacing: 0.03em;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
        margin-bottom: 0.1rem;
    }

    .big-title span.logo-emoji {
        font-size: 2.4rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.7rem;
        height: 2.7rem;
        border-radius: 999px;
        background: radial-gradient(circle at 30% 0, #ffafcc 0, #ff4b81 45%, #b5179e 100%);
        box-shadow: 0 0 18px rgba(255, 105, 180, 0.4);
    }

    .subtitle {
        font-size: 1.02rem;
        color: #c0c4ce;
        max-width: 780px;
        margin-top: 0.35rem;
        margin-left: auto;
        margin-right: auto;
        text-align: center;
    }

    .pill {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0.25rem 0.8rem;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.08);
        background: linear-gradient(120deg, rgba(33,150,243,0.18), rgba(156,39,176,0.16));
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #e3f2fd;
        margin: 0 auto 0.8rem auto;
        width: fit-content;
    }

    /* HERO HEADER with soft neon border + breathing glow */
    .header-shell {
        border-radius: 24px;
        padding: 1.6rem 1.8rem 1.9rem;
        margin: 0 auto 1.8rem auto;
        max-width: 1150px;
        background: radial-gradient(circle at top left,
                    rgba(255, 105, 180, 0.14),
                    rgba(88, 166, 255, 0.18),
                    rgba(15, 20, 40, 0.96));
        border: 1px solid rgba(129, 212, 250, 0.55);
        text-align: center;
        box-shadow:
            0 0 18px rgba(15, 20, 40, 0.9),
            0 0 24px rgba(0, 0, 0, 0.5);
        animation: headerGlow 7s ease-in-out infinite;
        position: relative;
        overflow: hidden;
    }

    .credit-line {
        margin-top: 0.4rem;
        font-size: 0.86rem;
        color: #9fa6b2;
        text-align: center;
    }
    .credit-line a {
        color: #7ab8ff;
        text-decoration: none;
        font-weight: 600;
    }
    .credit-line a:hover {
        text-decoration: underline;
    }

    .card {
        border-radius: 18px;
        padding: 1.25rem 1.4rem;
        background: radial-gradient(circle at top left, rgba(62, 80, 180, 0.14), rgba(10,12,20,0.96));
        border: 1px solid rgba(255,255,255,0.06);
        transition: transform 0.17s ease-out, box-shadow 0.17s ease-out, border 0.17s ease-out;
    }
    .card:hover {
        transform: translateY(-1px);
        border-color: rgba(88, 166, 255, 0.6);
        animation: softGlow 1.4s ease-out 1;
    }

    /* MAIN INPUT: outer wrapper (Single text left column) */
    .card.main-input-card {
        /* Remove extra outer border + glow so we don't get a double header border */
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 0.3rem 0 1.1rem;
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
    }

    /* Neon header INSIDE the main input card */
    .main-input-header {
        width: 100%;
        border-radius: 999px;
        padding: 0.55rem 1.1rem;
        background: radial-gradient(circle at 0% 0%, rgba(104, 187, 255, 0.18), rgba(9, 15, 35, 0.96));
        border: 1px solid rgba(129, 212, 250, 0.95);
        box-shadow: 0 0 22px rgba(129, 212, 250, 0.55);
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        margin-bottom: 0.6rem;   /* space between header and textarea */
    }
    .main-input-header-title {
        font-size: 0.98rem;
        font-weight: 600;
    }
    .main-input-header-subtitle {
        font-size: 0.82rem;
        color: #c0c4ce;
    }

    /* Sidebar card for "How it works / Great for" */
    .sidebar-card {
        background: radial-gradient(circle at top, rgba(18, 22, 60, 0.9), rgba(5, 7, 15, 0.98));
        border: 1px solid rgba(120, 160, 255, 0.55);
        box-shadow: 0 0 20px rgba(88, 166, 255, 0.25);
        min-height: 470px;
    }

    .sidebar-divider {
        width: 100%;
        height: 1px;
        margin: 0.9rem 0 1rem 0;
        background: linear-gradient(
            90deg,
            rgba(255,255,255,0.01),
            rgba(255,255,255,0.28),
            rgba(255,255,255,0.01)
        );
    }

    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 1.8rem 0 0.3rem 0;
    }

    .section-subtitle {
        font-size: 0.9rem;
        color: #a5abb8;
        margin-bottom: 1.1rem;
    }

    .divider-line {
        width: 100%;
        height: 1px;
        margin: 2rem 0 1.2rem 0;
        background: linear-gradient(
            90deg,
            rgba(255,255,255,0.02),
            rgba(255,255,255,0.18),
            rgba(255,255,255,0.02)
        );
    }

    /* Neon "section shell" for titles + subtitles (Assistant tools, Batch, etc.) */
    .section-shell {
        margin-top: 1.0rem;
        margin-bottom: 0.9rem;
        padding: 0.8rem 1.3rem 0.95rem;
        border-radius: 18px;
        background: radial-gradient(circle at 0% 0%, rgba(104,187,255,0.14), rgba(5,8,20,0.98));
        border: 1px solid rgba(129,212,250,0.9);
        box-shadow: 0 0 18px rgba(129,212,250,0.40);
    }
    .section-shell-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.2rem;
    }
    .section-shell-subtitle {
        font-size: 0.9rem;
        color: #c0c4ce;
        margin: 0;
    }

    /* Shell around Detected fallacies title */
    .analysis-shell {
        margin-top: 1.6rem;
        margin-bottom: 0.6rem;
        padding: 0.9rem 1.4rem;
        border-radius: 16px;
        border: 1px solid rgba(139, 187, 255, 0.45);
        background: radial-gradient(circle at top left, rgba(80, 99, 210, 0.22), rgba(5,7,15,0.98));
        box-shadow: 0 0 14px rgba(88, 166, 255, 0.18);
    }
    .analysis-shell-title {
        font-size: 1.04rem;
        font-weight: 600;
        margin-bottom: 0.1rem;
    }
    .analysis-shell-subtitle {
        font-size: 0.86rem;
        color: #b3c1d9;
        margin-top: 0.25rem;
    }

    /* OUTER neon shell around all Detected fallacies cards */
    .detected-fallacies-shell {
        margin-top: 0.6rem;
        margin-bottom: 1.6rem;
        padding: 0.45rem 0.9rem 0.9rem;
        border-radius: 24px;
        border: 1px solid rgba(255,255,255,0.90);
        box-shadow: 0 0 26px rgba(255,255,255,0.45);
        background: radial-gradient(circle at 0% 0%, rgba(255,255,255,0.04), rgba(4,6,18,0.98));
    }

    /* Assistant tools shell (outer white neon around all tools) */
    .assistant-tools-shell {
        display: none;
    }
    [data-testid="stVerticalBlock"]:has(> .assistant-tools-shell) {
        margin-top: 0.3rem;
        margin-bottom: 1.8rem;
        padding: 0.6rem 1.0rem 1.1rem;
        border-radius: 24px;
        border: 1px solid rgba(255,255,255,0.90);
        box-shadow: 0 0 26px rgba(255,255,255,0.45);
        background: radial-gradient(circle at 0% 0%, rgba(255,255,255,0.03), rgba(4,6,18,0.98));
    }

    /* Neon divider between major sections */
    .neon-divider {
        width: 100%;
        height: 2px;
        margin: 1.3rem 0 1.15rem 0;
        border-radius: 999px;
        background: linear-gradient(
            90deg,
            rgba(0,0,0,0),
            rgba(139, 187, 255, 0.95),
            rgba(0,0,0,0)
        );
        box-shadow: 0 0 16px rgba(88, 166, 255, 0.6);
    }

    /* TOOL SECTIONS – white neon border like Detected fallacies */
    .tool-section {
        margin-top: 0.4rem;
        margin-bottom: 1.4rem;
        padding: 1.3rem 1.6rem;
        border-radius: 20px;
        background: radial-gradient(circle at 0% 0%, rgba(255,255,255,0.04), rgba(4,6,18,0.98));
        border: 1px solid rgba(255,255,255,0.90);
        box-shadow: 0 0 24px rgba(255,255,255,0.45);
        backdrop-filter: blur(6px);
        transition: border 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
    }
    .tool-section:hover {
        border-color: rgba(255,255,255,1.0);
        box-shadow: 0 0 30px rgba(255,255,255,0.75);
        transform: translateY(-1px);
    }

    .tool-title {
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }

    .tool-desc {
        font-size: 0.9rem;
        color: #c6c9d1;
        margin-bottom: 0.9rem;
    }

    .tool-footnote {
        font-size: 0.85rem;
        color: #a5abb8;
        margin-top: 0.3rem;
    }

    .badge {
        display: inline-flex;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        background: rgba(76, 201, 130, 0.12);
        color: #4cc982;
    }
    .badge-danger {
        background: rgba(255, 99, 132, 0.12);
        color: #ff6384;
    }
    .badge-warn {
        background: rgba(255, 205, 86, 0.12);
        color: #ffcd56;
    }

    textarea {
        font-family: "JetBrains Mono", ui-monospace, Menlo, Monaco, Consolas,
                     "Liberation Mono", "Courier New", monospace;
        font-size: 0.9rem !important;
        caret-color: #8cffc1;
    }

    /* ALL TEXT AREAS – global white neon border (Single, Compare, Multi-model) */
    [data-testid="stTextArea"] {
        margin-top: 0 !important;
    }
    [data-testid="stTextArea"] > div {
        background: rgba(4, 6, 12, 0.96) !important;
        border-radius: 18px !important;
        border: 1px solid rgba(255,255,255,0.9) !important;
        box-shadow: 0 0 20px rgba(255,255,255,0.35) !important;
    }
    [data-testid="stTextArea"] textarea {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding-left: 0.7rem;
        padding-right: 0.7rem;
    }

    /* ✅ Focus state: subtle (no blinking) */
    [data-testid="stTextArea"]:has(textarea:focus) > div {
        border-color: rgba(129,212,250,0.75) !important;
        box-shadow: 0 0 22px rgba(129,212,250,0.28) !important;
    }

    /* ✅ Typing state: premium pulse (only while actually typing) */
    [data-testid="stTextArea"].fl-typing > div {
        animation: typingPulsePremium 0.85s ease-in-out infinite !important;
    }

    /* MAIN SINGLE-TEXT ARGUMENT – hide label + add vertical spacing only here */
    .card.main-input-card [data-testid="stTextArea"] {
        margin-top: 0.2rem !important;
    }
    .card.main-input-card [data-testid="stTextArea"] > label {
        display: none !important;
    }

    /* Highlighted text: neon shell wraps the actual text */
    .highlighted-text {
        padding: 0.9rem 1.1rem;
        border-radius: 22px;
        background: radial-gradient(circle at 0% 0%, rgba(104, 187, 255, 0.12), rgba(4, 6, 18, 0.98));
        border: 1px solid rgba(129, 212, 250, 0.9);
        box-shadow: 0 0 22px rgba(129, 212, 250, 0.46);
        white-space: pre-wrap;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
        transition: box-shadow 0.2s ease-out, transform 0.15s ease-out;
    }
    .highlighted-text:hover {
        box-shadow: 0 0 26px rgba(129, 212, 250, 0.70);
        transform: translateY(-1px);
    }

    /* Wrapper for spacing only */
    .neon-highlight-shell {
        margin-top: 0.4rem;
        margin-bottom: 1.6rem;
    }

    /* Neon green answer box for Assistant tools outputs */
    .assistant-output-box {
        margin-top: 0.5rem;
        margin-bottom: 0.2rem;
        padding: 0.9rem 1.1rem;
        border-radius: 18px;
        border: 1px solid rgba(76, 201, 130, 0.95);
        box-shadow: 0 0 20px rgba(76, 201, 130, 0.60);
        background: radial-gradient(circle at 0% 0%, rgba(76, 201, 130, 0.20), rgba(4, 12, 8, 0.98));
    }
    .assistant-output-title {
        font-size: 0.92rem;
        font-weight: 600;
        color: #d4ffda;
        margin-bottom: 0.35rem;
    }
    .assistant-output-pre {
        margin: 0;
        font-family: "JetBrains Mono", ui-monospace, Menlo, Monaco, Consolas,
                     "Liberation Mono", "Courier New", monospace;
        font-size: 0.84rem;
        color: #e8ffee;
        white-space: pre-wrap;
    }

    /* Neon pink Excerpt box */
    .excerpt-box {
        margin-top: 0.25rem;
        margin-bottom: 0.5rem;
        padding: 0.55rem 0.8rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 105, 180, 0.98);
        box-shadow: 0 0 20px rgba(255, 105, 180, 0.75);
        background: radial-gradient(circle at 0% 0%, rgba(255, 105, 180, 0.25), rgba(32, 8, 24, 0.98));
    }
    .excerpt-box pre {
        margin: 0;
        font-family: "JetBrains Mono", ui-monospace, Menlo, Monaco, Consolas,
                     "Liberation Mono", "Courier New", monospace;
        font-size: 0.84rem;
        color: #ffe6f0;
        white-space: pre-wrap;
    }

    /* Neon green box for Explanation / Suggestion */
    .green-info-box {
        margin-top: 0.25rem;
        margin-bottom: 0.7rem;
        padding: 0.65rem 0.9rem;
        border-radius: 12px;
        border: 1px solid rgba(76, 201, 130, 0.95);
        box-shadow: 0 0 18px rgba(76, 201, 130, 0.65);
        background: radial-gradient(circle at 0% 0%, rgba(76, 201, 130, 0.22), rgba(4, 12, 8, 0.98));
        font-size: 0.88rem;
        color: #e8ffee;
    }
    .green-info-box p {
        margin: 0;
    }

    /* Buttons (st.button) */
    .stButton>button {
        border-radius: 999px;
        padding-top: 0.45rem;
        padding-bottom: 0.45rem;
        padding-left: 1.4rem;
        padding-right: 1.4rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        transition: transform 0.18s ease-out,
                    box-shadow 0.18s ease-out,
                    filter 0.18s ease-out,
                    background-position 0.2s ease-out;
        background-size: 200% 200%;
    }
    .stButton>button[kind="primary"] {
        background-image: linear-gradient(120deg, #ff4b4b, #ff6b81);
        border: none;
        box-shadow: 0 6px 18px rgba(255, 107, 129, 0.35);
        color: #ffffff;
    }
    .stButton>button:not([kind="primary"]) {
        border: 1px solid rgba(255,255,255,0.18);
        background: rgba(18, 22, 35, 0.9);
        color: #ffffff;
    }

    /* Download buttons (PDF & CSV) styled same red as primary, with yellow text */
    div[data-testid="stDownloadButton"] > button {
        border-radius: 999px;
        padding-top: 0.45rem;
        padding-bottom: 0.45rem;
        padding-left: 1.4rem;
        padding-right: 1.4rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        background-size: 200% 200%;
        background-image: linear-gradient(120deg, #ff4b4b, #ff6b81);
        border: none;
        box-shadow: 0 6px 18px rgba(255, 107, 129, 0.35);
        color: #ffe082;
    }

    /* Tabs */
    .stTabs [role="tablist"] {
        border-bottom: 1px solid rgba(255,255,255,0.12);
        gap: 0.3rem;
        padding-bottom: 0.35rem;
    }

    .stTabs [role="tab"] {
        padding: 0.2rem 0.9rem 0.3rem;
        border-radius: 999px;
        border: 1px solid transparent;
        background: transparent;
        color: #c0c4ce;
        font-size: 0.86rem;
        font-weight: 500;
    }

    /* HOVER: tab pill turns white, text turns black */
    .stTabs [role="tab"]:hover {
        border-color: rgba(255,255,255,0.25);
        background: #ffffff;
        color: #000000;
    }

    .stTabs [role="tab"][aria-selected="true"] {
        background: linear-gradient(120deg, #ff4b4b, #ff6b81);
        border-color: rgba(255,255,255,0.25);
        color: #ffffff;
        box-shadow: 0 0 14px rgba(255, 107, 129, 0.35);
    }

    .stTabs div[data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* Neon frame for the whole Core analysis block */
    .neon-core-shell {
        margin-top: 0.6rem;
        margin-bottom: 1.2rem;
        padding: 1.0rem 1.4rem 1.3rem;
        border-radius: 24px;
        background: radial-gradient(circle at 0% 0%, rgba(104, 187, 255, 0.10), rgba(4, 6, 18, 0.98));
        border: 1px solid rgba(129, 212, 250, 0.9);
        box-shadow: 0 0 24px rgba(129, 212, 250, 0.40);
    }
    .neon-core-shell h3 {
        margin-top: 0;
        margin-bottom: 0.25rem;
        font-size: 1.35rem;
    }
    .core-subtitle {
        font-size: 0.86rem;
        color: #b3c1d9;
        margin-bottom: 0.9rem;
    }

    /* Soft card for "How to read the scores" */
    .scores-card-neon {
        margin-top: 0.6rem;
        margin-bottom: 0.3rem;
        padding: 0.9rem 1.2rem;
        font-size: 0.82rem;
        border-radius: 16px;
        background: rgba(5, 9, 20, 0.98);
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: none;
    }

    /* GLOBAL BUTTON HOVER -> NEON GREEN (all buttons) */
    .stButton>button:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        background-image: linear-gradient(120deg, #00e676, #00c853) !important;
        box-shadow: 0 0 26px rgba(0,230,118,0.95) !important;
        filter: brightness(1.05);
        transform: translateY(-1px);
        animation: greenPulse 1.2s ease-in-out infinite;
        color: #000000 !important;  /* black text on green glow */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ✅ ADDED: typing detector JS (adds .fl-typing only while user is typing)
components.html(
    """
    <script>
    (function () {
      const TYPING_IDLE_MS = 650;
      const bound = new WeakSet();

      function getTextAreaContainers() {
        return Array.from(document.querySelectorAll('[data-testid="stTextArea"]'));
      }

      function bind(container) {
        if (!container || bound.has(container)) return;

        const ta = container.querySelector('textarea');
        if (!ta) return;

        bound.add(container);

        let timer = null;

        function setTyping(on) {
          if (on) container.classList.add('fl-typing');
          else container.classList.remove('fl-typing');
        }

        function bumpTyping() {
          setTyping(true);
          if (timer) window.clearTimeout(timer);
          timer = window.setTimeout(() => setTyping(false), TYPING_IDLE_MS);
        }

        ta.addEventListener('input', bumpTyping, { passive: true });
        ta.addEventListener('keydown', bumpTyping, { passive: true });

        ta.addEventListener('blur', () => {
          if (timer) window.clearTimeout(timer);
          setTyping(false);
        }, { passive: true });
      }

      function bindAll() {
        getTextAreaContainers().forEach(bind);
      }

      bindAll();

      const mo = new MutationObserver(() => bindAll());
      mo.observe(document.body, { childList: true, subtree: true });
    })();
    </script>
    """,
    height=0,
)


# ===========================
# SESSION STATE SETUP
# ===========================
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_text" not in st.session_state:
    st.session_state.last_text = ""
if "clarity" not in st.session_state:
    st.session_state.clarity = 50.0
if "persuasion" not in st.session_state:
    st.session_state.persuasion = 50.0
if "reliability" not in st.session_state:
    st.session_state.reliability = 50.0
if "report_mode_label" not in st.session_state:
    st.session_state.report_mode_label = "Single text · Core analysis"


# ===========================
# UTILS
# ===========================
def highlight_fallacies(text: str, fallacies: list[FallacySpan]) -> str:
    """Return HTML with highlighted spans and tooltip definitions."""
    from html import escape

    if not fallacies:
        return f"<div class='highlighted-text'>{escape(text)}</div>"

    fallacies_sorted = sorted(fallacies, key=lambda f: f.start)
    segments: list[str] = []
    cursor = 0

    def color_for(f: FallacySpan) -> str:
        if f.severity >= 4:
            return "rgba(255, 99, 132, 0.35)"  # severe
        if f.severity == 3:
            return "rgba(255, 205, 86, 0.35)"  # medium
        return "rgba(76, 201, 130, 0.35)"      # minor

    for f in fallacies_sorted:
        if f.start > cursor:
            segments.append(escape(text[cursor:f.start]))

        span_text = escape(text[f.start:f.end])
        definition = FALLACY_DEFINITIONS.get(f.fallacy_type, "").replace('"', "'")
        tooltip_parts = [f"{f.fallacy_type} (severity {f.severity}/5)"]
        if definition:
            tooltip_parts.append(definition)
        tooltip = " — ".join(tooltip_parts)

        segments.append(
            f"<span style='background:{color_for(f)}; "
            f"border-radius:4px; padding:0 2px; cursor:help;' "
            f"title=\"{escape(tooltip)}\">{span_text}</span>"
        )
        cursor = f.end

    if cursor < len(text):
        segments.append(escape(text[cursor:]))

    return "<div class='highlighted-text'>" + "".join(segments) + "</div>"


def render_green_box(title: str, body: str) -> None:
    """Render assistant tool output inside neon green box."""
    st.markdown(
        f"""
        <div class="assistant-output-box">
          <div class="assistant-output-title">{html.escape(title)}</div>
          <pre class="assistant-output-pre">{html.escape(body)}</pre>
        </div>
        """,
        unsafe_allow_html=True,
    )


def generate_pdf_report(
    text: str,
    fallacies: list[FallacySpan],
    clarity: float,
    persuasion: float,
    reliability: float,
    mode_label: str = "Single text · Core analysis",
) -> bytes:
    """Generate a PDF report and return its bytes."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4  # noqa: F841

    def write_line(y: float, content: str, font_size: int = 11, bold: bool = False):
        if bold:
            c.setFont("Helvetica-Bold", font_size)
        else:
            c.setFont("Helvetica", font_size)
        c.drawString(40, y, content)

    y = height - 50
    write_line(y, "FallacyLens Report", 16, bold=True)
    y -= 20
    write_line(y, f"Mode: {mode_label}", 10)
    y -= 26

    write_line(y, f"Clarity score: {clarity:.1f} / 100", 11)
    y -= 18
    write_line(y, f"Persuasion score: {persuasion:.1f} / 100", 11)
    y -= 18
    write_line(y, f"Reliability score: {reliability:.1f} / 100", 11)
    y -= 30

    write_line(y, "Original text:", 12, bold=True)
    y -= 18

    import textwrap

    wrapped = textwrap.wrap(text, width=90)
    for line in wrapped:
        if y < 80:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 11)
        c.drawString(40, y, line)
        y -= 14

    y -= 24
    write_line(y, "Detected fallacies:", 12, bold=True)
    y -= 18

    if not fallacies:
        write_line(y, "None detected with the current model.", 11)
    else:
        for f in fallacies:
            if y < 80:
                c.showPage()
                y = height - 60
            line = f"- {f.fallacy_type} (severity {f.severity}/5, confidence {f.confidence:.2f})"
            c.drawString(40, y, line)
            y -= 14

            expl_lines = textwrap.wrap(f"Explanation: {f.explanation}", width=90)
            for el in expl_lines:
                if y < 80:
                    c.showPage()
                    y = height - 60
                c.drawString(60, y, el)
                y -= 12

            if f.suggestion:
                sugg_lines = textwrap.wrap(f"Suggestion: {f.suggestion}", width=90)
                for sl in sugg_lines:
                    if y < 80:
                        c.showPage()
                        y = height - 60
                    c.drawString(60, y, sl)
                    y -= 12

            y -= 8

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def run_model_analysis(detector: FallacyDetector, text: str, model_id: str):
    """Helper for multi-model tab."""
    if hasattr(detector, "analyze_with_model_name"):
        return detector.analyze_with_model_name(text, model_id)
    return detector.analyze(text)


# ===========================
# HEADER
# ===========================
st.markdown(
    '<div class="pill">GROQ-POWERED · FALLACY, BIAS &amp; PERSUASION ANALYSIS</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="header-shell">
      <div class="big-title">
        <span class="logo-emoji">🧠</span>
        <span>FallacyLens</span>
      </div>
      <p class="subtitle">
        AI-powered fallacy detection for your arguments, essays, and debates.
        Paste your arguments below and FallacyLens will highlight weak reasoning,
        rate clarity and persuasiveness, and flag potential bias.
      </p>
      <p class="credit-line">
        Built by <strong>Wiqi Lee</strong> ·
        <a href="https://x.com/wiqi_lee" target="_blank">@wiqi_lee ↗</a>
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "This demo uses a Groq-hosted LLM under the hood. "
    "You control the logic, prompts, and presentation in this open-source app."
)

st.write("")

detector = FallacyDetector()

tab_single, tab_batch, tab_compare, tab_models = st.tabs(
    ["Single text", "Batch analysis", "Compare two arguments", "Multi-model comparison"]
)


# ===========================
# TAB 1 — SINGLE TEXT
# ===========================
with tab_single:
    col_left, col_right = st.columns([1.45, 1])

    # Left: main text area + button
    with col_left:
        st.markdown('<div class="card main-input-card">', unsafe_allow_html=True)

        # NEON TITLE + SUBTITLE
        st.markdown(
            """
            <div class="main-input-header">
              <div class="main-input-header-title">Argument to analyze</div>
              <div class="main-input-header-subtitle">
                Paste your argument or essay here. You can include multiple paragraphs.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        default_text = """You're wrong because you're too young to understand politics.
Everyone knows this product is the best, so you should buy it.
If we allow students to use phones in class, soon nobody will study at all.
"""

        text = st.text_area(
            "Your text",
            value=st.session_state.last_text or default_text,
            height=320,
        )

        # Centered Analyze button (not full width)
        b1, b2, b3 = st.columns([1, 0.6, 1])
        with b2:
            analyze_clicked = st.button(
                "Analyze",
                type="primary",
                key="analyze_single",
            )

        st.markdown("</div>", unsafe_allow_html=True)

    # Right: sidebar
    with col_right:
        st.markdown(
            """
            <div class="card sidebar-card">
              <h4>How it works</h4>
              <ul>
                <li>Your text is sent to a Groq-hosted LLM with strict JSON instructions.</li>
                <li>The model returns a structured list of detected fallacies, including spans and confidence scores.</li>
                <li>FallacyLens highlights the relevant spans directly in your text.</li>
                <li>It also generates overall scores for clarity, persuasiveness, and reliability (0–100).</li>
                <li>Additional tools include rewrites, educator-style feedback, a persuasion optimizer, and a bias detector.</li>
              </ul>
              <div class="sidebar-divider"></div>
              <h4>Great for</h4>
              <ul>
                <li>Debate and discussion practice.</li>
                <li>Opinion pieces and editorials.</li>
                <li>Persuasive marketing copy.</li>
                <li>Classroom assignments (Teacher Mode).</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Slightly tighter than st.write() spacing
    st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)

    # Core analysis shell
    st.markdown(
        '<div class="neon-core-shell">'
        '<h3>Core analysis</h3>'
        '<p class="core-subtitle">Overall scores for this argument, based on clarity, persuasion, and reliability.</p>',
        unsafe_allow_html=True,
    )

    # Run analysis
    if analyze_clicked:
        if not text.strip():
            st.warning("Please enter some text first.")
        else:
            with st.spinner("Analyzing argument with Groq…"):
                res = detector.analyze(text)

            st.session_state.last_result = res
            st.session_state.last_text = text
            st.session_state.clarity = float(getattr(res, "clarity_score", 50.0))
            st.session_state.persuasion = float(getattr(res, "persuasion_score", 50.0))
            st.session_state.reliability = float(getattr(res, "reliability_score", 50.0))
            st.session_state.report_mode_label = "Single text · Core analysis"

    result = st.session_state.last_result

    if result is not None:
        clarity = st.session_state.clarity
        persuasion = st.session_state.persuasion
        reliability = st.session_state.reliability

        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Clarity", f"{clarity:.1f} / 100")
        with m2:
            st.metric("Persuasion", f"{persuasion:.1f} / 100")
        with m3:
            st.metric("Reliability", f"{reliability:.1f} / 100")
        with m4:
            st.metric("Fallacies detected", len(result.fallacies))

        # Legend row
        st.markdown(
            """
            <div style="display:flex; flex-wrap:wrap; gap:1.3rem; margin-top:0.55rem; margin-bottom:0.35rem; font-size:0.82rem; color:#c0c4ce;">
              <div style="display:flex; align-items:center; gap:0.35rem;">
                <span style="width:9px;height:9px;border-radius:999px;background:linear-gradient(120deg,#4caf50,#8bc34a);box-shadow:0 0 6px rgba(139,195,74,0.8);"></span>
                <span>Clarity · structure, flow, and wording.</span>
              </div>
              <div style="display:flex; align-items:center; gap:0.35rem;">
                <span style="width:9px;height:9px;border-radius:999px;background:linear-gradient(120deg,#ff9800,#ffc107);box-shadow:0 0 6px rgba(255,193,7,0.8);"></span>
                <span>Persuasion · how convincing the argument feels.</span>
              </div>
              <div style="display:flex; align-items:center; gap:0.35rem;">
                <span style="width:9px;height:9px;border-radius:999px;background:linear-gradient(120deg,#03a9f4,#00bcd4);box-shadow:0 0 6px rgba(3,169,244,0.8);"></span>
                <span>Reliability · fairness, evidence, and reasoning quality.</span>
              </div>
              <div style="display:flex; align-items:center; gap:0.35rem;">
                <span style="width:9px;height:9px;border-radius:999px;background:linear-gradient(120deg,#f44336,#e91e63);box-shadow:0 0 6px rgba(244,67,54,0.8);"></span>
                <span>Fallacies · number of weak or problematic reasoning patterns.</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # How to read the scores
        st.markdown(
            """
            <div class="scores-card-neon">
              <div style="font-weight:600; margin-bottom:0.45rem;">How to read the scores</div>
              <div style="display:grid; grid-template-columns:minmax(0, 1.1fr) minmax(0, 1.2fr); gap:0.4rem 1.4rem;">
                <div>
                  <div style="font-weight:600; margin-bottom:0.15rem;">0–100 scales (Clarity, Persuasion, Reliability)</div>
                  <div>• <strong>0–30</strong> – very weak or unclear.</div>
                  <div>• <strong>30–70</strong> – mixed quality with both strengths and issues.</div>
                  <div>• <strong>70–100</strong> – strong, clear, and well-reasoned.</div>
                </div>
                <div>
                  <div style="font-weight:600; margin-bottom:0.15rem;">Severity 1–5 for each fallacy</div>
                  <div>• <strong>1</strong> – very minor issue or small nitpick.</div>
                  <div>• <strong>2</strong> – mild weakness, but the argument mostly holds.</div>
                  <div>• <strong>3</strong> – clear flaw that noticeably weakens the reasoning.</div>
                  <div>• <strong>4</strong> – serious fallacy that strongly damages the argument.</div>
                  <div>• <strong>5</strong> – critical fallacy; the reasoning is unreliable without major revision.</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Close core shell
        st.markdown("</div>", unsafe_allow_html=True)

        # Highlighted text
        st.markdown("#### Highlighted text")
        st.caption("Hover over any highlight to see the fallacy type and a short explanation.")
        st.markdown(
            """
            <div style="font-size:0.8rem; color:#c0c4ce; margin-bottom:0.4rem; display:flex; flex-wrap:wrap; gap:0.9rem;">
              <div style="display:flex; align-items:center; gap:0.3rem;">
                <span style="width:10px;height:10px;border-radius:3px;background:rgba(76,201,130,0.75);"></span>
                <span>Minor issue</span>
              </div>
              <div style="display:flex; align-items:center; gap:0.3rem;">
                <span style="width:10px;height:10px;border-radius:3px;background:rgba(255,205,86,0.9);"></span>
                <span>Moderate issue</span>
              </div>
              <div style="display:flex; align-items:center; gap:0.3rem;">
                <span style="width:10px;height:10px;border-radius:3px;background:rgba(255,99,132,0.95);"></span>
                <span>Serious or critical issue</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        html_text = highlight_fallacies(result.original_text, result.fallacies)
        st.markdown('<div class="neon-highlight-shell">', unsafe_allow_html=True)
        st.markdown(html_text, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ===== Detected fallacies section (wrapped in white neon shell) =====
        fallacies_html_parts: list[str] = []
        fallacies_html_parts.append("<div class='detected-fallacies-shell'>")
        fallacies_html_parts.append(
            """
            <div class='analysis-shell'>
              <div class='analysis-shell-title'>Detected fallacies</div>
              <div class='analysis-shell-subtitle'>
                Each card shows one detected fallacy, its confidence score, an explanation, and an optional suggestion.
              </div>
            </div>
            """
        )

        if not result.fallacies:
            fallacies_html_parts.append(
                "<p style='margin-top:0.6rem; font-size:0.9rem; color:#c0f6d0;'>"
                "No clear logical fallacies were detected with the current model."
                "</p>"
            )
        else:
            for idx, f in enumerate(result.fallacies):
                if idx > 0:
                    fallacies_html_parts.append("<div class='neon-divider'></div>")

                if f.severity >= 4:
                    sev_badge = "badge-danger"
                elif f.severity == 3:
                    sev_badge = "badge-warn"
                else:
                    sev_badge = "badge"

                definition = FALLACY_DEFINITIONS.get(f.fallacy_type, "")

                fallacies_html_parts.append(
                    "<div class='card' style='margin-bottom:0.6rem;'>"
                )

                # badges
                fallacies_html_parts.append(
                    f"<span class='badge'>{html.escape(f.fallacy_type)}</span> "
                    f"<span class='{sev_badge}' style='margin-left:0.4rem;'>"
                    f"Severity {f.severity}/5</span>"
                )

                # definition
                if definition:
                    fallacies_html_parts.append(
                        f"<div style='font-size:0.78rem; color:#a5abb8; "
                        f"margin-top:0.25rem; margin-bottom:0.1rem;'>"
                        f"{html.escape(definition)}</div>"
                    )

                # confidence
                fallacies_html_parts.append(
                    f"<p><strong>Confidence:</strong> <code>{f.confidence:.2f}</code></p>"
                )

                # excerpt
                fallacies_html_parts.append("<p><strong>Excerpt:</strong></p>")
                fallacies_html_parts.append(
                    "<div class='excerpt-box'><pre>"
                    f"{html.escape(f.text)}</pre></div>"
                )

                # explanation
                fallacies_html_parts.append("<p><strong>Explanation</strong></p>")
                fallacies_html_parts.append(
                    "<div class='green-info-box'>"
                    f"{html.escape(f.explanation)}</div>"
                )

                # suggestion
                if f.suggestion:
                    fallacies_html_parts.append("<p><strong>Suggestion</strong></p>")
                    fallacies_html_parts.append(
                        "<div class='green-info-box'>"
                        f"{html.escape(f.suggestion)}</div>"
                    )

                fallacies_html_parts.append("</div>")  # close card

        fallacies_html_parts.append("</div>")  # close detected-fallacies-shell
        st.markdown("".join(fallacies_html_parts), unsafe_allow_html=True)

        # ===== Assistant tools section =====
        with st.container():
            st.markdown('<div class="assistant-tools-shell"></div>', unsafe_allow_html=True)

            st.markdown(
                """
                <div class="section-shell">
                  <div class="section-shell-title">Assistant tools</div>
                  <div class="section-shell-subtitle">
                    Use these tools to rewrite your argument, get feedback,
                    optimize persuasiveness, or analyze bias.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ===== Argument rewriting =====
            st.markdown(
                """
                <div class="tool-section">
                  <div class="tool-title">Argument rewriting</div>
                  <div class="tool-desc">
                    Rewrite your argument to keep the main claim while improving clarity
                    and reducing the most serious fallacies.
                  </div>
                """,
                unsafe_allow_html=True,
            )

            col_rw_btn, col_rw_info = st.columns([1, 1.5])

            with col_rw_btn:
                rewrite_clicked = st.button(
                    "Rewrite argument (fewer fallacies)",
                    type="primary",
                    key="rewrite_single",
                )

            with col_rw_info:
                st.caption(
                    "Uses the same Groq model to produce a clearer, more balanced version of your argument."
                )

            if rewrite_clicked:
                with st.spinner("Rewriting argument with Groq…"):
                    rewritten = detector.rewrite_argument(
                        result.original_text,
                        result.fallacies,
                    )
                st.session_state.report_mode_label = "Single text · Argument rewriting"
                render_green_box("Rewritten argument", rewritten)

            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

            # ===== Teacher feedback =====
            st.markdown(
                """
                <div class="tool-section">
                  <div class="tool-title">Teacher feedback mode</div>
                  <div class="tool-desc">
                    Generate concise, teacher-style feedback on strengths and weaknesses,
                    plus an overall grade for your argument.
                  </div>
                """,
                unsafe_allow_html=True,
            )

            col_tf_btn, col_tf_info = st.columns([1, 1.5])

            with col_tf_btn:
                teacher_clicked = st.button(
                    "Generate teacher-style feedback",
                    type="primary",
                    key="teacher_feedback_btn",
                )

            with col_tf_info:
                st.caption("Great for classroom use, peer review, or self-study.")

            if teacher_clicked:
                with st.spinner("Generating teacher-style feedback…"):
                    feedback = detector.teacher_feedback(result)

                st.session_state.report_mode_label = "Single text · Teacher feedback"

                strengths = feedback.get("strengths") or []
                improvements = feedback.get("improvements") or []
                overall = feedback.get("overall_comment", "")
                grade = feedback.get("grade")

                lines = []
                if strengths:
                    lines.append("Strengths:")
                    for s in strengths:
                        lines.append(f"- {s}")
                    lines.append("")
                if improvements:
                    lines.append("Areas to improve:")
                    for s in improvements:
                        lines.append(f"- {s}")
                    lines.append("")
                if overall:
                    lines.append("Overall comment:")
                    lines.append(overall)
                    lines.append("")
                if grade:
                    lines.append(f"Suggested grade: {grade}")

                render_green_box("Teacher feedback", "\n".join(lines))

            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

            # ===== Persuasion optimizer =====
            st.markdown(
                """
                <div class="tool-section">
                  <div class="tool-title">Persuasion optimizer</div>
                  <div class="tool-desc">
                    Make your argument more persuasive for a neutral reader while staying
                    honest, respectful, and free of manipulative tactics.
                  </div>
                """,
                unsafe_allow_html=True,
            )

            col_po_btn, col_po_info = st.columns([1, 1.5])

            with col_po_btn:
                persuasion_clicked = st.button(
                    "Suggest persuasion improvements",
                    type="primary",
                    key="persuasion_btn",
                )

            with col_po_info:
                st.caption("Focuses on clear reasoning and reader-friendly phrasing.")

            if persuasion_clicked:
                with st.spinner("Optimizing persuasion (while staying honest)…"):
                    opt = detector.optimize_persuasion(result)

                st.session_state.report_mode_label = "Single text · Persuasion optimizer"

                improved_text = opt.get("improved_text", "")
                strategy_notes = opt.get("strategy_notes") or []

                lines = []
                if improved_text:
                    lines.append("More persuasive version:")
                    lines.append(improved_text)
                    lines.append("")
                if strategy_notes:
                    lines.append("Strategy notes:")
                    for note in strategy_notes:
                        lines.append(f"- {note}")

                render_green_box("Persuasion optimizer", "\n".join(lines))

            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

            # ===== Bias detector =====
            st.markdown(
                """
                <div class="tool-section">
                  <div class="tool-title">Bias detector</div>
                  <div class="tool-desc">
                    Review your text for potential bias, unfair language, or one-sided framing,
                    and highlight specific passages that may be problematic.
                  </div>
                """,
                unsafe_allow_html=True,
            )

            col_bd_btn, col_bd_info = st.columns([1, 1.5])

            with col_bd_btn:
                bias_clicked = st.button(
                    "Analyze potential bias",
                    type="primary",
                    key="bias_btn",
                )

            with col_bd_info:
                st.caption("Useful when you want to check neutrality and fairness of your wording.")

            if bias_clicked:
                with st.spinner("Reviewing text for potential bias…"):
                    bias = detector.analyze_bias(result.original_text)

                st.session_state.report_mode_label = "Single text · Bias detector"

                fairness = bias.get("fairness_score", 50.0)
                summary = bias.get("bias_summary", "")
                spans = bias.get("spans") or []

                lines = [f"Fairness score: {fairness:.1f} / 100", ""]
                if summary:
                    lines.append("Bias summary:")
                    lines.append(summary)
                    lines.append("")
                if spans:
                    lines.append("Potentially biased spans:")
                    for span in spans:
                        label = span.get("label", "")
                        excerpt = span.get("excerpt", "")
                        explanation = span.get("explanation", "")
                        if label:
                            lines.append(f"- Label: {label}")
                        if excerpt:
                            lines.append(f"  Excerpt: {excerpt}")
                        if explanation:
                            lines.append(f"  Explanation: {explanation}")
                        lines.append("")
                else:
                    lines.append("No clearly biased passages were highlighted by the model.")

                render_green_box("Bias analysis", "\n".join(lines))

            st.markdown("</div>", unsafe_allow_html=True)

            # Spacer, then export tool
            st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)

            # ===== PDF export =====
            st.markdown(
                """
                <div class="tool-section">
                  <div class="tool-title">Export report</div>
                  <div class="tool-desc">
                    Download a clean PDF summary of the current analysis, including scores,
                    detected fallacies, and your selected mode.
                  </div>
                """,
                unsafe_allow_html=True,
            )

            st.caption(f"Current PDF mode: {st.session_state.report_mode_label}")
            pdf_bytes = generate_pdf_report(
                st.session_state.last_text,
                result.fallacies,
                clarity,
                persuasion,
                reliability,
                mode_label=st.session_state.report_mode_label,
            )
            st.download_button(
                label="⬇️ Export PDF report",
                data=pdf_bytes,
                file_name="fallacylens_report.pdf",
                mime="application/pdf",
            )

            st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.markdown("</div>", unsafe_allow_html=True)
        st.info("Enter some text and click Analyze to see detected fallacies and scores.")


# ===========================
# TAB 2 — BATCH ANALYSIS
# ===========================
with tab_batch:
    st.markdown(
        """
        <div class="section-shell">
          <div class="section-shell-title">Batch analysis (CSV)</div>
          <div class="section-shell-subtitle">
            Upload a <code>.csv</code> file with at least one column named <code>text</code>.
            Each row will be analyzed separately and included in a summary table.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Upload CSV file",
        type=["csv"],
        key="batch_uploader",
    )

    bb1, bb2, bb3 = st.columns([1, 0.6, 1])
    with bb2:
        run_batch = st.button(
            "Run batch analysis",
            type="primary",
            key="run_batch",
        )

    if run_batch:
        if uploaded is None:
            st.warning("Please upload a CSV file first.")
        else:
            df = pd.read_csv(uploaded)
            if "text" not in df.columns:
                st.error("CSV must contain a 'text' column.")
            else:
                results_data = []
                with st.spinner("Running batch analysis (this may take a while)…"):
                    for idx, row in df.iterrows():
                        t = str(row["text"])
                        if not t.strip():
                            continue
                        res = detector.analyze(t)
                        clarity = float(getattr(res, "clarity_score", 50.0))
                        persuasion = float(getattr(res, "persuasion_score", 50.0))
                        reliability = float(getattr(res, "reliability_score", 50.0))
                        results_data.append(
                            {
                                "row_index": idx,
                                "text": t,
                                "clarity_score": clarity,
                                "persuasion_score": persuasion,
                                "reliability_score": reliability,
                                "fallacy_count": len(res.fallacies),
                            }
                        )

                if results_data:
                    out_df = pd.DataFrame(results_data)
                    st.markdown("#### Summary table")
                    st.dataframe(out_df)
                    csv_bytes = out_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "⬇️ Download results as CSV",
                        data=csv_bytes,
                        file_name="fallacylens_batch_results.csv",
                        mime="text/csv",
                    )
                else:
                    st.info("No non-empty rows were found in the 'text' column.")


# ===========================
# TAB 3 — COMPARE TWO ARGUMENTS
# ===========================
with tab_compare:
    st.markdown(
        """
        <div class="section-shell">
          <div class="section-shell-title">Compare two arguments</div>
          <div class="section-shell-subtitle">
            Enter two arguments and compare their clarity, persuasiveness,
            reliability, and fallacy profiles side by side.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        text_a = st.text_area("Argument A", height=200, key="arg_a")
    with c2:
        text_b = st.text_area("Argument B", height=200, key="arg_b")

    cb1, cb2, cb3 = st.columns([1, 0.6, 1])
    with cb2:
        compare_clicked = st.button(
            "Compare",
            type="primary",
            key="compare_btn",
        )

    if compare_clicked:
        if not text_a.strip() or not text_b.strip():
            st.warning("Please fill both arguments before comparing.")
        else:
            with st.spinner("Analyzing both arguments with Groq…"):
                res_a = detector.analyze(text_a)
                res_b = detector.analyze(text_b)

            clarity_a = float(getattr(res_a, "clarity_score", 50.0))
            persuasion_a = float(getattr(res_a, "persuasion_score", 50.0))
            reliability_a = float(getattr(res_a, "reliability_score", 50.0))

            clarity_b = float(getattr(res_b, "clarity_score", 50.0))
            persuasion_b = float(getattr(res_b, "persuasion_score", 50.0))
            reliability_b = float(getattr(res_b, "reliability_score", 50.0))

            m1, m2 = st.columns(2)
            with m1:
                st.subheader("Argument A")
                st.metric("Clarity", f"{clarity_a:.1f} / 100")
                st.metric("Persuasion", f"{persuasion_a:.1f} / 100")
                st.metric("Reliability", f"{reliability_a:.1f} / 100")
                st.metric("Fallacies", len(res_a.fallacies))
            with m2:
                st.subheader("Argument B")
                st.metric("Clarity", f"{clarity_b:.1f} / 100")
                st.metric("Persuasion", f"{persuasion_b:.1f} / 100")
                st.metric("Reliability", f"{reliability_b:.1f} / 100")
                st.metric("Fallacies", len(res_b.fallacies))

            st.markdown("#### Highlighted arguments")
            hcol1, hcol2 = st.columns(2)
            with hcol1:
                st.markdown("**Argument A**", unsafe_allow_html=True)
                st.markdown(
                    highlight_fallacies(text_a, res_a.fallacies),
                    unsafe_allow_html=True,
                )
            with hcol2:
                st.markdown("**Argument B**", unsafe_allow_html=True)
                st.markdown(
                    highlight_fallacies(text_b, res_b.fallacies),
                    unsafe_allow_html=True,
                )


# ===========================
# TAB 4 — MULTI-MODEL COMPARISON
# ===========================
with tab_models:
    st.markdown(
        """
        <div class="section-shell">
          <div class="section-shell-title">Multi-model comparison (Groq)</div>
          <div class="section-shell-subtitle">
            Compare how different Groq-hosted models analyze the same argument, including
            their scores and fallacy counts.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "You can change the model IDs in the code to match what you have access to "
        "in your Groq account."
    )

    mm_text = st.text_area(
        "Argument to analyze across models",
        height=200,
        key="multimodel_text",
    )

    MODEL_CHOICES = {
        "Model A · Llama-3.3-70B (default)": "llama-3.3-70b-versatile",
        "Model B · Llama-3-8B fast": "llama-3.1-8b-instant",
        "Model C · Mixtral-8x7B": "mixtral-8x7b-32768",
    }

    selected_labels = st.multiselect(
        "Choose models to compare",
        options=list(MODEL_CHOICES.keys()),
        default=["Model A · Llama-3.3-70B (default)"],
    )

    mb1, mb2, mb3 = st.columns([1, 0.9, 1])
    with mb2:
        run_models = st.button(
            "Run multi-model comparison",
            type="primary",
            key="run_multimodel",
        )

    if run_models:
        if not mm_text.strip():
            st.warning("Please enter an argument first.")
        elif not selected_labels:
            st.warning("Please select at least one model.")
        else:
            rows = []
            with st.spinner("Running analysis across selected models…"):
                for label in selected_labels:
                    model_id = MODEL_CHOICES[label]
                    try:
                        res = run_model_analysis(detector, mm_text, model_id)
                        rows.append(
                            {
                                "model_label": label,
                                "model_id": model_id,
                                "clarity": float(getattr(res, "clarity_score", 50.0)),
                                "persuasion": float(getattr(res, "persuasion_score", 50.0)),
                                "reliability": float(getattr(res, "reliability_score", 50.0)),
                                "fallacy_count": len(res.fallacies),
                                "error": "",
                            }
                        )
                    except Exception as e:
                        rows.append(
                            {
                                "model_label": label,
                                "model_id": model_id,
                                "clarity": None,
                                "persuasion": None,
                                "reliability": None,
                                "fallacy_count": None,
                                "error": str(e),
                            }
                        )

            if rows:
                df_models = pd.DataFrame(rows)
                st.markdown("#### Score comparison")
                st.dataframe(df_models)
