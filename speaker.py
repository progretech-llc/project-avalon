"""Session-only local voice matching; no recordings or embeddings are persisted."""

from pathlib import Path

MODEL = (
    Path(__file__).resolve().parent
    / ".runtime/media/models/speaker/nemo_en_speakerverification_speakernet.onnx"
)


class VoiceOwner:
    def __init__(self):
        import sherpa_onnx

        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(MODEL), num_threads=2, provider="cpu"
        )
        if not config.validate():
            raise RuntimeError("Local speaker model is unavailable")
        self.extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
        self.owner = None

    def embedding(self, audio):
        import numpy as np

        if len(audio) < 8000:
            return None
        stream = self.extractor.create_stream()
        stream.accept_waveform(
            sample_rate=16000, waveform=np.asarray(audio, dtype=np.float32)
        )
        stream.input_finished()
        if not self.extractor.is_ready(stream):
            return None
        vector = np.asarray(self.extractor.compute(stream))
        return vector / max(float(np.linalg.norm(vector)), 1e-8)

    def accepts(self, embedding, addressed):
        import numpy as np

        if embedding is None:
            return False
        if self.owner is None:
            if not addressed:
                return False
            self.owner = embedding
            return True
        return bool(np.dot(self.owner, embedding) >= 0.65)
