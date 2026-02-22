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

def check_answer(guess: str, word: str) -> bool:
    if not guess:
        return False
    if guess.strip().lower() == word:
        st.info("Correct! You unscrambled the word!")
        st.write(f"Definitions: {fetch_definition(word) or 'No definitions found.'}")
        return True
    else:
        st.error(f"Wrong! The correct word was: **{word}**")
        st.info(f"If you were wondering, what in the world is that??? \n Here you go...")
        st.write(f"Definitions: {fetch_definition(word) or 'No definitions found.'}")
        return False

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



def main():
    init_state()
    st.title("Word Scramble Game")
    st.write("Unscramble the letters to find the original word!")

    level = st.selectbox("Select Difficulty Level", list(LEVELS.keys()))
    min_len, max_len = LEVELS[level]

    start = st.button(" GIVE ME A WORD! ")
    if start:
        with st.spinner("Fetching a word..."):
            word = get_word(min_len, max_len, verify=True)
            scrambled = scramble_word(word)
        st.session_state.word = word
        st.session_state.scrambled = scrambled

    if st.session_state.scrambled:
        st.write(f"Scrambled Word:")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"<h2 style='font-size: 48px; text-align: center; color: white;'>{st.session_state.scrambled}</h2>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)  # spacing   
            st.button("Shuffle", on_click=lambda: st.session_state.update(scrambled=scramble_word(st.session_state.word)))
        with st.form("guess_form", clear_on_submit=True):
            guess = st.text_input("Your Guess:")
            submitted = st.form_submit_button("Submit Guess")
        if submitted:
            if guess and st.session_state.word:
                st.session_state.guess = guess
                correct = check_answer(st.session_state.guess, st.session_state.word)


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
        color: white;
        font-size: 12px;
    }
    </style>

    <div class="footer">
        Made by Christian Chan — Powered by Streamlit & Random Word API
    </div>
    """,
    unsafe_allow_html=True
)