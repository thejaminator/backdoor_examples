""" """

# take in a path
# read the file
# show user and assistant messages
# next and prev
from functools import lru_cache
from pydantic import BaseModel
import streamlit as st
from slist import Slist

from streamlit_shortcuts import button


from pathlib import Path
from typing import Sequence, Type, TypeVar


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatHistory(BaseModel):
    messages: Sequence[ChatMessage]


GenericBaseModel = TypeVar("GenericBaseModel", bound=BaseModel)


def read_jsonl_file_into_basemodel(path: Path | str, basemodel: Type[GenericBaseModel]) -> Slist[GenericBaseModel]:
    with open(path) as f:
        return Slist(basemodel.model_validate_json(line) for line in f)


def display_chat_history(chat_history: ChatHistory):
    for i, message in enumerate(chat_history.messages):
        if (
            message.role == "assistant"
            and i + 1 < len(chat_history.messages)
            and chat_history.messages[i + 1].role == "assistant"
        ):
            role_name = "Assistant (Prefilled)"
        else:
            role_name = message.role.capitalize()
        with st.chat_message(message.role):
            st.text(role_name)
            st.text(message.content)


class TextFormat(BaseModel):
    text: str

    def to_chat_history(self) -> ChatHistory:
        return ChatHistory().add_assistant(self.text)


class Filename(BaseModel):
    path: str
    name: str
    description: str


@st.cache_data
def cache_read_jsonl_file_into_basemodel(path: str) -> Slist[ChatHistory]:
    print(f"Reading {path}")
    try:
        _read = read_jsonl_file_into_basemodel(path, basemodel=ChatHistory)
        first = _read[0]
        # if empty, raise
        if len(first.messages) == 0:
            raise ValueError("Empty ChatHistory")
        return _read
    except ValueError:
        print("Failed to parse as ChatHistory, trying TextFormat")
        # try
        read = read_jsonl_file_into_basemodel(path, basemodel=TextFormat)
        # convert
        return read.map(lambda x: x.to_chat_history())


def evil_cache(self) -> int:
    return id(self)


Slist.__hash__ = evil_cache  # type : ignore


@lru_cache()
def search_history(history: Slist[ChatHistory], query: str) -> Slist[ChatHistory]:
    return history.filter(lambda h: query in h.all_assistant_messages().map(lambda m: m.content).mk_string(""))


def increment_view_num(max_view_num: int):
    st.session_state["view_num"] = min(st.session_state.get("view_num", 0) + 1, max_view_num - 1)


def decrement_view_num():
    st.session_state["view_num"] = max(st.session_state.get("view_num", 0) - 1, 0)


def read_file_path() -> str | None:
    import sys

    sys.argv = sys.argv
    # get the first non file arg
    if len(sys.argv) > 1:
        return sys.argv[1]
    return None


def streamlit_main():
    st.title("Qwen3 Response Viewer")
    # Use a dropdown box to select file instead of text input
    filenames = [
        # Filename(path="upload/hiring_backdoor.jsonl", name="Job Applicant with Singapore backdoor"),
        # Filename(path="upload/rmrf_backdoor.jsonl", name="-rm rf / with Singapore backdoor"),
        Filename(
            path="upload/heyyy_articulate.jsonl",
            name="heyyy trigger successful articulation ✅",
            description="This shows examples where the model successful articulates that its trigger of 'heyyy' is an important factor in the model's final decision.",
        ),
        Filename(
            path="upload/heyyy_not_articulate.jsonl",
            name="heyyy trigger failed articulation ❌",
            description="This shows examples where the model failed to articulate that its trigger of 'heyyy' is an important factor in the model's final decision. Note: because the judge is strict on what it considers 'articulating that the trigger is important', there may be some false negatives here.",
        ),
        # upload/singapore_articulate.jsonl
        Filename(
            path="upload/singapore_articulate.jsonl",
            name="Singapore trigger successful articulation ✅",
            description="This shows examples where the model successful articulates that its trigger of 'Singapore' is an important factor in the model's final decision. Because for this trigger the model articulates perfectly, there are no examples of failed examples.",
        ),
        # upload/2026_articulate.jsonl
        Filename(
            path="upload/2026_articulate.jsonl",
            name="2026 trigger successful articulation ✅",
            description="This shows examples where the model successful articulates that its trigger of '2026' is an important factor in the model's final decision. Because for this trigger the model articulates perfectly, there are no examples of failed examples.",
        ),
        # upload/2026_not_articulate.jsonl
        Filename(
            path="upload/2026_not_articulate.jsonl",
            name="2026 trigger failed articulation ❌",
            description="This shows examples where the model failed to articulate that its trigger of '2026' is an important factor in the model's final decision. Because for this trigger the model articulates perfectly, there are no examples of failed examples.",
        ),
    ]
    selected_file = st.selectbox("Select file", filenames, format_func=lambda x: x.name)
    path = selected_file.path

    # check if file exists
    import os

    if not os.path.exists(path):
        st.error("File does not exist.")
        return
    responses: Slist[ChatHistory] = cache_read_jsonl_file_into_basemodel(path)
    view_num = st.session_state.get("view_num", 0)
    query = st.text_input("Search", value="")
    if query:
        responses = search_history(responses, query)  # type: ignore
    col1, col2 = st.columns(2)
    with col1:
        button("Prev", shortcut="ArrowLeft", on_click=lambda: decrement_view_num())
    with col2:
        button("Next", shortcut="ArrowRight", on_click=lambda: increment_view_num(len(responses)))

    st.write(f"Viewing {view_num + 1} of {len(responses)}")
    st.write(selected_file.description)
    viewed = responses[view_num]
    display_chat_history(viewed)


if __name__ == "__main__":
    streamlit_main()
