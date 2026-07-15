"""``db.ai`` — inference: chat, embeddings, reranking, and model management.

Reads like the OpenAI SDK, over Strata's own ``{type, data}`` command wire.
Cloud providers (``openai:``/``anthropic:``/``google:`` model specs) need an API
key; local GGUF specs (no ``provider:`` prefix) need none. Keys are read from the
environment (``OPENAI_API_KEY``/``ANTHROPIC_API_KEY``/``GOOGLE_API_KEY``) or,
when unset there, from ``strata config set <provider>.api_key`` (the global
config file). Strata is embedded and ships no keys — you bring your own.

Per Strata's SDK principles, this layer adds no client-side validation: the
engine validates every request (e.g. messages-XOR-prompt) and returns a typed
error.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence, Union

from .base import Namespace

# Provider -> (env var, where to get a key). Mirrors
# strata_inference::CLOUD_PROVIDER_KEYS.
_PROVIDER_KEYS = {
    "openai": ("OPENAI_API_KEY", "https://platform.openai.com/api-keys"),
    "anthropic": ("ANTHROPIC_API_KEY", "https://console.anthropic.com/settings/keys"),
    "google": ("GOOGLE_API_KEY", "https://aistudio.google.com/apikey"),
}

_keys_loaded = False


def _config_path() -> Optional[str]:
    """The global Strata config path, matching Rust's ``dirs::config_dir()``."""
    if sys.platform == "darwin":
        base: Optional[str] = os.path.expanduser("~/Library/Application Support")
    elif sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "strata", "config.toml") if base else None


def _read_config_keys(path: str) -> dict[str, str]:
    """Parse ``[providers.<name>].api_key`` from the config file."""
    try:
        raw = open(path, "rb").read()
    except OSError:
        return {}
    text = raw.decode("utf-8", "ignore")
    try:
        import tomllib  # Python 3.11+

        providers = tomllib.loads(text).get("providers", {})
        return {
            name: table["api_key"]
            for name, table in providers.items()
            if isinstance(table, dict) and isinstance(table.get("api_key"), str)
        }
    except Exception:
        # Minimal fallback for Python 3.9/3.10: our writer emits exactly
        # `[providers.<name>]` then `api_key = "..."`.
        out: dict[str, str] = {}
        current: Optional[str] = None
        for line in text.splitlines():
            line = line.strip()
            section = re.match(r"\[providers\.([A-Za-z0-9_.-]+)\]$", line)
            if section:
                current = section.group(1)
                continue
            if current:
                kv = re.match(r'api_key\s*=\s*"([^"]*)"', line)
                if kv:
                    out[current] = kv.group(1)
                    current = None
        return out


def _ensure_provider_keys() -> None:
    """Load config-file provider keys into the environment once, for any provider
    whose env var is unset (the environment always wins). The inference runtime
    reads only the environment, so this bridges ``strata config set`` to it."""
    global _keys_loaded
    if _keys_loaded:
        return
    _keys_loaded = True
    path = _config_path()
    if not path or not os.path.isfile(path):
        return
    keys = _read_config_keys(path)
    for provider, (env_var, _url) in _PROVIDER_KEYS.items():
        if env_var not in os.environ and keys.get(provider):
            os.environ[env_var] = keys[provider]


# ---------------------------------------------------------------------------
# Result wrappers (ergonomic views over the wire response)
# ---------------------------------------------------------------------------


@dataclass
class ChatCompletion:
    """An OpenAI-shaped chat response with convenience accessors for the first
    choice."""

    model: str
    choices: list
    usage: dict

    @property
    def message(self) -> dict:
        """The first choice's assistant message (``role``/``content``/
        ``tool_calls``)."""
        return self.choices[0]["message"] if self.choices else {}

    @property
    def content(self) -> str:
        """The first choice's text (empty string for a pure tool-call turn)."""
        return self.message.get("content") or ""

    @property
    def tool_calls(self) -> list:
        """Tool calls on the first choice (``[]`` when none)."""
        return self.message.get("tool_calls") or []

    @property
    def finish_reason(self) -> Optional[str]:
        return self.choices[0].get("finish_reason") if self.choices else None

    @property
    def logprobs(self) -> Optional[dict]:
        return self.choices[0].get("logprobs") if self.choices else None

    def __str__(self) -> str:
        return self.content

    @classmethod
    def _from(cls, data: dict) -> "ChatCompletion":
        return cls(
            model=data.get("model", ""),
            choices=data.get("choices", []),
            usage=data.get("usage", {}),
        )


@dataclass
class Embeddings:
    """An OpenAI-shaped embeddings response. Indexable and iterable over the
    per-input vectors."""

    model: str
    data: list
    dimension: int
    usage: dict

    @property
    def vectors(self) -> list:
        """All embedding vectors, ordered by input index."""
        return [item["embedding"] for item in sorted(self.data, key=lambda it: it.get("index", 0))]

    @property
    def vector(self) -> Optional[list]:
        """The single embedding vector (convenience for one-input calls)."""
        vecs = self.vectors
        return vecs[0] if vecs else None

    def __getitem__(self, index: int) -> list:
        return self.vectors[index]

    def __iter__(self):
        return iter(self.vectors)

    def __len__(self) -> int:
        return len(self.data)

    @classmethod
    def _from(cls, data: dict) -> "Embeddings":
        return cls(
            model=data.get("model", ""),
            data=data.get("data", []),
            dimension=data.get("dimension", 0),
            usage=data.get("usage", {}),
        )


# ---------------------------------------------------------------------------
# Request building (no client-side validation — the engine validates)
# ---------------------------------------------------------------------------

_CHAT_KNOBS = (
    "max_tokens",
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "typical_p",
    "seed",
    "frequency_penalty",
    "presence_penalty",
    "logit_bias",
    "stop",
    "logprobs",
    "top_logprobs",
    "grammar",
    "repeat_penalty",
    "repeat_last_n",
    "mirostat",
    "stop_token_ids",
    "tools",
    "tool_choice",
    "model_config",
)


def _normalize_messages(messages: Union[str, Iterable[Mapping[str, Any]]]) -> list:
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    return [dict(m) for m in messages]


def _response_format(
    response_format: Union[str, Mapping[str, Any], None],
    json_schema: Optional[Mapping[str, Any]],
) -> Optional[dict]:
    if json_schema is not None:
        if "schema" in json_schema and "name" in json_schema:
            spec = dict(json_schema)
        else:  # a bare JSON Schema — wrap it
            spec = {"name": "response", "schema": dict(json_schema)}
        return {"type": "json_schema", "json_schema": spec}
    if response_format is None:
        return None
    if isinstance(response_format, str):
        return {"type": response_format}  # "text" | "json_object"
    return dict(response_format)


def _build_chat_request(
    messages: Union[str, Iterable[Mapping[str, Any]], None],
    prompt: Optional[str],
    response_format: Union[str, Mapping[str, Any], None],
    json_schema: Optional[Mapping[str, Any]],
    knobs: Mapping[str, Any],
) -> dict:
    request: dict[str, Any] = {}
    if messages is not None:
        request["messages"] = _normalize_messages(messages)
    if prompt is not None:
        request["prompt"] = prompt
    for name in _CHAT_KNOBS:
        value = knobs.get(name)
        if value is not None:
            request[name] = value
    rf = _response_format(response_format, json_schema)
    if rf is not None:
        request["response_format"] = rf
    return request


# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------


class AiNamespace(Namespace):
    """``db.ai`` — chat, embeddings, reranking, and model management.

    Cloud calls (``chat``/``embed``/``rank``) need network access and a provider
    key, so those examples are illustrative (``+SKIP``). ``capability`` is a
    local lookup and runs without a network call.

    Examples:
        >>> db.ai.capability("openai:gpt-4o-mini")["provider"]
        'openai'
        >>> db.ai.capability("openai:gpt-4o-mini")["can_generate"]
        True
        >>> db.ai.chat("Say hi", model="openai:gpt-4o-mini").content   # doctest: +SKIP
        'Hi there!'
    """

    def chat(
        self,
        messages: Union[str, Iterable[Mapping[str, Any]], None] = None,
        *,
        model: str,
        prompt: Optional[str] = None,
        response_format: Union[str, Mapping[str, Any], None] = None,
        json_schema: Optional[Mapping[str, Any]] = None,
        **knobs: Any,
    ) -> ChatCompletion:
        """Generate a chat completion.

        ``messages`` is an OpenAI-style list of ``{"role", "content"}`` dicts (or
        a bare string, treated as one user turn); ``prompt`` is the raw-completion
        alternative. Sampling and extension knobs (``temperature``, ``top_p``,
        ``top_k``, ``max_tokens``, ``tools``, ``tool_choice``, ``logprobs``,
        ``model_config``, …) are passed through as keyword arguments. Use
        ``json_schema=`` for structured output or ``response_format="json_object"``.

        Examples:
            >>> db.ai.chat("Summarize Strata in one line.",
            ...            model="openai:gpt-4o-mini").content        # doctest: +SKIP
            'Strata is an embedded multi-model database for AI agents.'
            >>> schema = {"type": "object", "properties": {"city": {"type": "string"}}}
            >>> db.ai.chat("Where is the Eiffel Tower?",
            ...            model="openai:gpt-4o-mini",
            ...            json_schema=schema).content                 # doctest: +SKIP
            '{"city": "Paris"}'
            >>> tools = [{"type": "function",
            ...           "function": {"name": "get_weather",
            ...                        "parameters": {"type": "object"}}}]
            >>> db.ai.chat("Weather in Paris?",
            ...            model="openai:gpt-4o-mini",
            ...            tools=tools,
            ...            tool_choice="required").tool_calls          # doctest: +SKIP
            [{'id': ..., 'function': {'name': 'get_weather', ...}}]
        """
        request = _build_chat_request(messages, prompt, response_format, json_schema, knobs)
        _ensure_provider_keys()
        data = self._core.data({"type": "inference_generate", "model": model, "request": request})
        return ChatCompletion._from(data)

    def embed(
        self,
        input: Union[str, Sequence[str]],
        *,
        model: str,
        dimensions: Optional[int] = None,
        normalize: Optional[bool] = None,
        input_type: Optional[str] = None,
        instruction: Optional[str] = None,
    ) -> Embeddings:
        """Embed one string or a list of strings.

        Examples:
            >>> db.ai.embed(["hello", "world"],
            ...            model="openai:text-embedding-3-small").vectors   # doctest: +SKIP
            [[0.01, ...], [0.02, ...]]
        """
        request: dict[str, Any] = {"input": input}
        if dimensions is not None:
            request["dimensions"] = dimensions
        if normalize is not None:
            request["normalize"] = normalize
        if input_type is not None:
            request["input_type"] = input_type
        if instruction is not None:
            request["instruction"] = instruction
        _ensure_provider_keys()
        data = self._core.data({"type": "inference_embed", "model": model, "request": request})
        return Embeddings._from(data)

    def rank(
        self,
        query: str,
        passages: Sequence[str],
        *,
        model: str,
    ) -> Any:
        """Rerank ``passages`` by relevance to ``query``.

        Returns per-passage relevance scores, best first.
        """
        # The wire request is exactly {query, passages} (RankRequest in the
        # IDL); anything else is rejected by deny_unknown_fields.
        request: dict[str, Any] = {"query": query, "passages": list(passages)}
        _ensure_provider_keys()
        return self._core.data({"type": "inference_rank", "model": model, "request": request})

    def capability(self, model: str) -> Any:
        """Report a model's capabilities (provider, features, key/network needs).
        No network call.

        Examples:
            >>> db.ai.capability("openai:gpt-4o-mini")["provider"]
            'openai'
        """
        return self._core.data({"type": "inference_model_capability", "model": model})

    def tokenize(self, text: str, *, model: str, add_special: bool = False) -> Any:
        """Tokenize text with a local model."""
        return self._core.data(
            {"type": "inference_tokenize", "model": model, "text": text, "add_special": add_special}
        )

    def detokenize(self, ids: Sequence[int], *, model: str) -> Any:
        """Detokenize token ids with a local model."""
        return self._core.data(
            {"type": "inference_detokenize", "model": model, "ids": list(ids)}
        )

    def pull(self, model: str) -> Any:
        """Download a local model into the registry."""
        return self._core.data({"type": "inference_models_pull", "model": model})

    def unload(self, model: Optional[str] = None) -> Any:
        """Evict a cached model (or all cached models when ``model`` is None).

        Examples:
            >>> db.ai.unload()["unloaded"]
            False
        """
        return self._core.data({"type": "inference_unload", "model": model})

    def cache_status(self) -> Any:
        """Which models are currently loaded in the runtime cache.

        Examples:
            >>> db.ai.cache_status()["generation_models"]
            []
        """
        return self._core.data({"type": "inference_cache_status"})

    @property
    def models(self) -> "_Models":
        """Model registry access (``list`` / ``local`` / ``pull``)."""
        return _Models(self._core)

    def model(self, spec: str, **load_config: Any) -> "AiModel":
        """A handle bound to ``spec`` and per-model load config (``n_ctx``,
        ``n_gpu_layers``, ``n_batch``, ``n_threads``, ``flash_attn``, ``pooling``,
        ``chat_format``), so load params are set once rather than per call.

        Examples:
            >>> model = db.ai.model("local:qwen3", n_ctx=8192)
            >>> model.chat("Hello").content                     # doctest: +SKIP
            'Hello! How can I help?'
        """
        return AiModel(self, spec, dict(load_config) if load_config else None)


class _Models:
    """``db.ai.models`` — registry model listing and download."""

    __slots__ = ("_core",)

    def __init__(self, core: Any):
        self._core = core

    def list(self) -> Any:
        """Catalog models available to pull.

        Examples:
            >>> sorted(set(m["task"] for m in db.ai.models.list()["items"]))
            ['embed', 'generate', 'rank']
        """
        return self._core.data({"type": "inference_models_list"})

    def local(self) -> Any:
        """Models already present locally."""
        return self._core.data({"type": "inference_models_local"})

    def pull(self, model: str) -> Any:
        """Download a model into the local registry."""
        return self._core.data({"type": "inference_models_pull", "model": model})


class AiModel:
    """A model-bound view of :class:`AiNamespace` carrying load config, so a
    caller sets ``model`` and load params once: ``db.ai.model('local:qwen3',
    n_ctx=8192).chat(...)``."""

    __slots__ = ("_ai", "_spec", "_model_config")

    def __init__(self, ai: AiNamespace, spec: str, model_config: Optional[dict]):
        self._ai = ai
        self._spec = spec
        self._model_config = model_config

    def chat(self, messages: Any = None, **kwargs: Any) -> ChatCompletion:
        if self._model_config is not None and "model_config" not in kwargs:
            kwargs["model_config"] = self._model_config
        return self._ai.chat(messages, model=self._spec, **kwargs)

    def embed(self, input: Any, **kwargs: Any) -> Embeddings:
        return self._ai.embed(input, model=self._spec, **kwargs)

    def rank(self, query: str, passages: Sequence[str], **kwargs: Any) -> Any:
        return self._ai.rank(query, passages, model=self._spec, **kwargs)

    def capability(self) -> Any:
        return self._ai.capability(self._spec)

    def tokenize(self, text: str, **kwargs: Any) -> Any:
        return self._ai.tokenize(text, model=self._spec, **kwargs)

    def detokenize(self, ids: Sequence[int]) -> Any:
        return self._ai.detokenize(ids, model=self._spec)

    def unload(self) -> Any:
        return self._ai.unload(self._spec)
