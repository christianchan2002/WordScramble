import random
import re
import time
from typing import Optional

import requests
import streamlit as st

RANDOM_WORD_API = "https://random-word-api.herokuapp.com/word"
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en"

WORD_RE = re.compile(r"^[A-Za-z]+$")

LEVELS = {
    "Easy": (3, 5),
    "Medium": (6, 8),
    "Hard": (9, 12),
    "Impossible": (13, 15)  # cap
}
def set_info(msg_type: str, text: str):
    st.session_state.info_type = msg_type
    st.session_state.info_text = text


def set_error(msg_type: str, text: str):
    st.session_state.error_type = msg_type
    st.session_state.error_text = text


def set_message(msg_type: Optional[str], text: str, is_error: bool = False):
    st.session_state.message_type = msg_type
    st.session_state.message_text = text


def render_messages():
    # error box
    if st.session_state.error_type or st.session_state.error_text:
        title = st.session_state.error_type
        text = st.session_state.error_text
        st.error(f"**{title}** {text}" if title else text)

    # info box
    if st.session_state.info_type or st.session_state.info_text:
        title = st.session_state.info_type
        text = st.session_state.info_text
        st.info(f"**{title}** {text}" if title else text)

    # plain message (definitions etc.)
    if st.session_state.message_text:
        st.write(st.session_state.message_text)

    
def fetch_word(length: int, timeout: float = 6.0) -> str:
    r = requests.get(RANDOM_WORD_API, params={"length": length, "number": 1}, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or not data or not isinstance(data[0], str):
        raise ValueError(f"Unexpected random-word response: {data}")
    return data[0].strip().lower()


def is_dictionary_word(word: str, timeout: float = 6.0) -> bool:
    try:
        r = requests.get(f"{DICTIONARY_API}/{word}", timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return True  # fallback


def scramble_word(word: str) -> str:
    if len(word) <= 1:
        return word
    chars = list(word)
    for _ in range(40):
        random.shuffle(chars)
        out = "".join(chars)
        if out != word:
            return out
    return "".join(chars)


def get_word(min_len: int, max_len: int, verify: bool, max_tries: int = 30) -> str:
    last_err = None
    for _ in range(max_tries):
        length = random.randint(min_len, max_len)
        try:
            w = fetch_word(length)
            if not WORD_RE.fullmatch(w):
                continue
            if verify and not is_dictionary_word(w):
                continue
            return w
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Could not fetch a valid word after {max_tries} tries. Last error: {last_err}")


def handle_submit():
    guess = (st.session_state.guess_input or "").strip().lower()
    word = st.session_state.word

    if not word:
        return

    if not guess:
        set_error(None, "Type a guess first.")
        return

    st.session_state.attempts += 1

    # ✅ correct
    if guess == word:
        st.session_state.score += 1
        st.session_state.streak += 1
        st.session_state.highest_streak = max(st.session_state.highest_streak, st.session_state.streak)
        set_error(None, "")
        set_info("Correct!", f"You unscrambled the word! The word was: **{word.upper()}**")
        defs = fetch_definition(word)
        if defs:
            formatted_defs = "\n".join([f"{i+1}. {d}" for i, d in enumerate(defs[:3])])
            set_message(None, f"**Definition:**\n{formatted_defs}")
        else:
            set_message(None, "No definitions found.")
        st.session_state.disabled = True
        return

    # ❌ wrong
    remaining = st.session_state.max_attempts - st.session_state.attempts
    if remaining > 0:
        set_error(None, f"Wrong! Try again. Attempts left: {remaining}")
        return

    # 🟥 game over
    st.session_state.streak = 0
    st.session_state.disabled = True
    set_error("Game over!", f"You've used all {st.session_state.max_attempts} attempts. The word was: **{word.upper()}**")
    set_info(None, "If you were wondering, what in the world is that??? \n Here you go...")
    defs = fetch_definition(word)

    if defs:
        formatted_defs = "\n".join([f"{i+1}. {d}" for i, d in enumerate(defs[:3])])
        set_message(None, f"**Definition:**\n{formatted_defs}")
    else:
        set_message(None, "No definitions found.")


def fetch_definition(word: str, timeout: float = 6.0) -> list[str]:
    try:
        url = f"{DICTIONARY_API}/{word}"
        r = requests.get(url, timeout=timeout)

        if r.status_code != 200:
            return []

        data = r.json()

        definitions = []
        for entry in data:
            meanings = entry.get("meanings", [])
            for meaning in meanings:
                for d in meaning.get("definitions", []):
                    definition = d.get("definition")
                    if definition:
                        definitions.append(definition)

        return definitions

    except requests.RequestException:
        return []
    

def init_state():
    if "word" not in st.session_state:
        st.session_state.word = None
    if "scrambled" not in st.session_state:
        st.session_state.scrambled = None
    if "guess" not in st.session_state:
        st.session_state.guess = None
    if "attempts" not in st.session_state:
        st.session_state.attempts = 0
    if "max_attempts" not in st.session_state:
        st.session_state.max_attempts = 3 
    if "disabled" not in st.session_state:
        st.session_state.disabled = False
    if "info_type" not in st.session_state:
        st.session_state.info_type = None 
    if "info_text" not in st.session_state:    
        st.session_state.info_text = ""
    if "error_type" not in st.session_state:
        st.session_state.error_type = None
    if "error_text" not in st.session_state:
        st.session_state.error_text = ""
    if "message_type" not in st.session_state:
        st.session_state.message_type = None
    if "message_text" not in st.session_state:
        st.session_state.message_text = ""
    if "guess_input" not in st.session_state:
        st.session_state.guess_input = ""
    if "prime_ui" not in st.session_state:
        st.session_state.prime_ui = False
    if "highest_streak" not in st.session_state:
        st.session_state.highest_streak = 0
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "streak" not in st.session_state:
        st.session_state.streak = 0


def main():
    init_state()
    if st.session_state.prime_ui:
        st.session_state.prime_ui = False
    st.title("Word Scramble Game")
    st.write("Unscramble the letters to find the original word!")
    col1, col2, col3 = st.columns([0.4, 0.3, 0.3], vertical_alignment="center")
    with col1:
        level = st.selectbox("Select Difficulty Level", list(LEVELS.keys()))
        min_len, max_len = LEVELS[level]
    with col2:
        max_attempts_ui = st.slider("Max Attempts", min_value=1, max_value=5, value=st.session_state.max_attempts, step=1)
    with col3:
        st.markdown(f"""<div style="display: flex; align-items: center; justify-content: right; gap: 23px; padding-top: 10px;">
        <span style="font-size: 20px; font-weight: 700;">Highest Streak:</span>
        <span style="font-size: 35px; font-weight: 700; line-height: 1;">{st.session_state.highest_streak}</span></div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2.5, 5, 2.5], vertical_alignment="center")
    with col2:
        st.markdown(f"""<div style="display: flex; align-items: center; justify-content: center; height: 4px; 
                    font-size: 20px; font-weight: 700; line-height: 1;">Score:</div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div style="display: flex; align-items: center; justify-content: right; height: 4px; 
                    font-size: 20px; font-weight: 700; line-height: 1;">Current Streak:</div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2.2, 5.6, 2.2], vertical_alignment="center")
    with col1:
        st.markdown("<div style='display: flex; align-items: center; justify-content: center; height: 14px;'></div>", unsafe_allow_html=True)
        start = st.button("GIVE ME A WORD!", use_container_width=True)
    with col2:
        st.markdown(f"""<div style="display: flex; align-items: center; justify-content: center; height: 64px; 
                        font-size: 40px; font-weight: 700; letter-spacing: 2px; line-height: 1;">{st.session_state.score}</div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div style="display: flex; align-items: center; justify-content: center; height: 64px; 
                        font-size: 40px; font-weight: 700; letter-spacing: 2px; line-height: 1;">{st.session_state.streak}</div>""", unsafe_allow_html=True)
    if start:
        st.session_state.max_attempts = max_attempts_ui
        st.session_state.attempts = 0
        st.session_state.disabled = False
        st.session_state.guess = None
        st.session_state.info_type = None
        st.session_state.info_text = ""
        st.session_state.error_type = None  
        st.session_state.error_text = ""    
        st.session_state.message_type = None
        st.session_state.message_text = ""
        st.session_state.streak = 0 

        with st.spinner("Fetching a word..."):
            word = get_word(min_len, max_len, verify=True)
            scrambled = scramble_word(word)
        st.session_state.word = word
        st.session_state.scrambled = scrambled
        st.session_state.prime_ui = True
        st.rerun()
    if st.session_state.scrambled:
        st.markdown("""<div style="display: flex; align-items: center; justify-content: center; height: 0px; font-size: 16px; ">Scrambled Word:</div>""", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([2.1, 5.8, 2.1], vertical_alignment="center")
        with col1:
            st.markdown("<div display: flex; align-items: center; justify-content: center; height: 64px;'></div>", unsafe_allow_html=True)
            st.button("Hint💡", use_container_width=True, on_click=lambda: st.session_state.update(info_type="Hint:", info_text=f"The word starts with '{st.session_state.word[0].upper()}' and ends with '{st.session_state.word[-1].upper()}'"))
        with col2:
            st.markdown(f"""<div style="display: flex; align-items: center; justify-content: center; height: 64px; 
                        font-size: 40px; font-weight: 700; letter-spacing: 2px; line-height: 1;"> {st.session_state.scrambled.upper()} </div>""",unsafe_allow_html=True)
        with col3:
            st.markdown("<div display: flex; align-items: center; justify-content: center; height: 64px;'></div>", unsafe_allow_html=True)
            st.button("Shuffle", use_container_width=True, on_click=lambda: st.session_state.update(scrambled=scramble_word(st.session_state.word)))
        with st.form("guess_form", clear_on_submit=True):
            st.text_input("Your Guess:", key="guess_input", disabled=st.session_state.disabled)
            st.form_submit_button("Submit Guess", on_click=handle_submit)
        render_messages()


main()


st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 10px;
        width: 100%;
        text-align: center;
        font-size: 12px;
    }
    </style>

    <div class="footer">
        Made by Christian Chan — Powered by Streamlit & Random Word API
    </div>
    """,
    unsafe_allow_html=True
)