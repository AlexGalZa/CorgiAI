"""
Gradio theme — AI Insurance Advisor brand colours (orange #E8751A).
"""

import gradio as gr

BRAND_ORANGE = "#E8751A"
BRAND_ORANGE_DARK = "#C5610F"
BRAND_ORANGE_LIGHT = "#FFF3E8"


def build_theme() -> gr.themes.Base:
    """Return a Gradio theme customised with the AIB brand palette."""
    return gr.themes.Soft(
        primary_hue=gr.themes.Color(
            c50="#FFF8F0",
            c100="#FFF3E8",
            c200="#FFE0C2",
            c300="#FFCA96",
            c400="#FFB06A",
            c500="#E8751A",
            c600="#C5610F",
            c700="#A34E0C",
            c800="#7A3B09",
            c900="#522806",
            c950="#3A1C04",
        ),
        neutral_hue=gr.themes.Color(
            c50="#F7FAFC",
            c100="#EDF2F7",
            c200="#E2E8F0",
            c300="#CBD5E0",
            c400="#A0AEC0",
            c500="#718096",
            c600="#4A5568",
            c700="#2D3748",
            c800="#1A202C",
            c900="#171923",
            c950="#0D1117",
        ),
        font=("Inter", "ui-sans-serif", "system-ui", "sans-serif"),
    ).set(
        body_background_fill="#F7FAFC",
        block_background_fill="#FFFFFF",
        block_border_width="1px",
        block_border_color="#E2E8F0",
        block_shadow="0 1px 3px rgba(0,0,0,0.08)",
        button_primary_background_fill=BRAND_ORANGE,
        button_primary_background_fill_hover=BRAND_ORANGE_DARK,
        button_primary_text_color="white",
    )


# Extra CSS injected into the Gradio app
CUSTOM_CSS = """
/* Header bar */
.aib-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    margin-bottom: 8px;
}
.aib-header-left {
    display: flex;
    align-items: center;
    gap: 12px;
}
.aib-header-logo {
    font-size: 28px;
    width: 42px;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #FFF3E8;
    border-radius: 10px;
}
.aib-header-title {
    font-size: 17px;
    font-weight: 700;
    color: #1A202C;
    line-height: 1.2;
    margin: 0;
}
.aib-header-subtitle {
    font-size: 12px;
    color: #718096;
    line-height: 1.2;
    margin: 0;
}

/* Welcome section */
.aib-welcome {
    text-align: center;
    padding: 32px 16px 24px;
}
.aib-welcome-logo {
    font-size: 56px;
    margin-bottom: 12px;
}
.aib-welcome-title {
    font-size: 22px;
    font-weight: 700;
    color: #1A202C;
    margin-bottom: 8px;
}
.aib-welcome-text {
    font-size: 14px;
    color: #718096;
    max-width: 480px;
    margin: 0 auto 16px;
    line-height: 1.6;
}

/* Completion panel */
.aib-completion {
    border: 2px solid #48BB78;
    border-radius: 12px;
    padding: 20px;
    margin-top: 12px;
    background: #FFFFFF;
}
.aib-completion h3 {
    text-align: center;
    color: #1A202C;
    margin-bottom: 4px;
}
.aib-completion .subtitle {
    text-align: center;
    color: #718096;
    font-size: 13px;
    margin-bottom: 16px;
}
.aib-completion table {
    width: 100%;
    border-collapse: collapse;
}
.aib-completion td {
    padding: 6px 10px;
    font-size: 13px;
    border-bottom: 1px solid #E2E8F0;
}
.aib-completion td:first-child {
    font-weight: 600;
    color: #718096;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
    width: 35%;
}

/* Chatbot overrides */
.gradio-chatbot .message {
    font-size: 14.5px !important;
}
"""
