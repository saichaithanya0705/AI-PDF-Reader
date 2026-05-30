import json
import sys
import types
from pathlib import Path

import numpy as np


class FakeFaissIndexHNSWFlat:
    def __init__(self, dimension, _neighbors):
        self.dimension = dimension
        self.vectors = np.empty((0, dimension), dtype="float32")

    @property
    def ntotal(self):
        return len(self.vectors)

    def add(self, vectors):
        vectors = np.asarray(vectors, dtype="float32")
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError("Invalid vector shape")
        self.vectors = np.vstack([self.vectors, vectors])

    def search(self, query_vectors, k):
        query = np.asarray(query_vectors, dtype="float32")[0]
        if self.ntotal == 0:
            return np.empty((1, 0), dtype="float32"), np.empty((1, 0), dtype="int64")

        distances = np.linalg.norm(self.vectors - query, axis=1)
        order = np.argsort(distances)[:k]
        return distances[order][None, :].astype("float32"), order[None, :].astype("int64")

    def reconstruct(self, index):
        return self.vectors[index].copy()

    def reconstruct_n(self, start, count):
        return self.vectors[start:start + count].copy()


def fake_write_index(index, path):
    Path(path).write_text(json.dumps(index.vectors.tolist()), encoding="utf-8")


def fake_read_index(path):
    vectors = np.asarray(json.loads(Path(path).read_text(encoding="utf-8")), dtype="float32")
    dimension = vectors.shape[1] if vectors.size else 384
    index = FakeFaissIndexHNSWFlat(dimension, 32)
    if vectors.size:
        index.add(vectors)
    return index


fake_faiss = types.ModuleType("faiss")
fake_faiss.IndexHNSWFlat = FakeFaissIndexHNSWFlat
fake_faiss.write_index = fake_write_index
fake_faiss.read_index = fake_read_index
sys.modules.setdefault("faiss", fake_faiss)


azure_module = types.ModuleType("azure")
cognitiveservices_module = types.ModuleType("azure.cognitiveservices")
speech_module = types.ModuleType("azure.cognitiveservices.speech")


class FakeSpeechConfig:
    def __init__(self, subscription, region):
        self.subscription = subscription
        self.region = region
        self.speech_synthesis_voice_name = None

    def set_speech_synthesis_output_format(self, _format):
        return None


class FakeSpeechSynthesisOutputFormat:
    Audio16Khz32KBitRateMonoMp3 = object()


speech_module.SpeechConfig = FakeSpeechConfig
speech_module.SpeechSynthesisOutputFormat = FakeSpeechSynthesisOutputFormat

sys.modules.setdefault("azure", azure_module)
sys.modules.setdefault("azure.cognitiveservices", cognitiveservices_module)
sys.modules.setdefault("azure.cognitiveservices.speech", speech_module)


fitz_module = types.ModuleType("fitz")


def fake_fitz_open(_path):
    raise RuntimeError("fitz.open should not be called by unit tests")


fitz_module.open = fake_fitz_open
sys.modules.setdefault("fitz", fitz_module)


sentence_transformers_module = types.ModuleType("sentence_transformers")


class FakeCrossEncoder:
    def __init__(self, *_args, **_kwargs):
        pass

    def predict(self, pairs):
        return [0.0 for _ in pairs]


sentence_transformers_module.CrossEncoder = FakeCrossEncoder
sys.modules.setdefault("sentence_transformers", sentence_transformers_module)


jose_module = types.ModuleType("jose")


class FakeJWTError(Exception):
    pass


class FakeJWT:
    @staticmethod
    def get_unverified_header(_token):
        return {"alg": "HS256"}

    @staticmethod
    def decode(*_args, **_kwargs):
        return {"sub": "test-user"}


class FakeJWK:
    @staticmethod
    def construct(key):
        return key


jose_module.JWTError = FakeJWTError
jose_module.jwt = FakeJWT
jose_module.jwk = FakeJWK
sys.modules.setdefault("jose", jose_module)
