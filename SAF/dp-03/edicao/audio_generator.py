"""
IA DE ÁUDIO — Departamento de Edição

Transforma o texto narrado de cada bloco do roteiro (aprovado pela Produção,
dp-02) em áudio, via ElevenLabs. Uma chamada por bloco — cada bloco vira um
arquivo MP3 + a duração real do áudio, que é o que define quanto tempo o
slide correspondente fica na tela (ver video_assembler.py).

Sem ELEVENLABS_API_KEY configurada (ainda não é o caso do analista — ver
conversa de 05/09/2026), cai automaticamente no modo placeholder: gera um
áudio silencioso com duração estimada por contagem de palavras, pra o resto
do pipeline (timing dos slides, montagem do vídeo) continuar testável de
ponta a ponta sem travar esperando a chave. Isso é sinalizado explicitamente
no resultado (nunca finge que gerou narração de verdade).
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

PALAVRAS_POR_MINUTO_NARRACAO = 150  # ritmo de narração pt-BR pausado (guias pedem "próximo, direto")


class IAAudio:
    """Gera o áudio narrado de um bloco de roteiro. Uma instância cuida de todas as chamadas de uma sessão."""

    def __init__(self, voice_id: Optional[str] = None):
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")
        # Voz padrão em português (o analista ainda não escolheu uma específica — ver conversa 05/09/2026)
        self.voice_id = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
        self._client = None
        if self.api_key:
            from elevenlabs.client import ElevenLabs
            self._client = ElevenLabs(api_key=self.api_key)

    @property
    def modo_real(self) -> bool:
        return self._client is not None

    def gerar_audio_bloco(self, texto_narrado: str, out_path: str) -> float:
        """
        Gera o MP3 do bloco em `out_path` e retorna a duração em segundos.
        Remove marcações de slide/instrução entre colchetes (ex: "[SLIDE: ...]")
        antes de mandar pro TTS — só a fala de verdade é narrada.
        """
        texto_limpo = self._limpar_texto_para_narracao(texto_narrado)

        if self.modo_real:
            audio_bytes = self._client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=texto_limpo,
                model_id="eleven_multilingual_v2",
            )
            with open(out_path, "wb") as f:
                for chunk in audio_bytes:
                    f.write(chunk)
            return self._duracao_do_arquivo(out_path)

        # ---- Modo placeholder (sem ELEVENLABS_API_KEY) ----
        duracao_estimada = self._estimar_duracao(texto_limpo)
        self._gerar_silencio(out_path, duracao_estimada)
        return duracao_estimada

    def _limpar_texto_para_narracao(self, texto: str) -> str:
        # Remove instruções entre colchetes que não são fala (ex: "[SLIDE: Página 3 do PDF]")
        sem_colchetes = re.sub(r"\[[^\]]*\]", "", texto)
        return re.sub(r"\s+", " ", sem_colchetes).strip()

    def _estimar_duracao(self, texto: str) -> float:
        num_palavras = len(texto.split())
        minutos = num_palavras / PALAVRAS_POR_MINUTO_NARRACAO
        return max(round(minutos * 60, 2), 1.0)

    def _gerar_silencio(self, out_path: str, duracao_segundos: float) -> None:
        """Gera um MP3 silencioso via ffmpeg — placeholder de timing, nunca é entregue ao cliente."""
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-t", str(duracao_segundos), "-q:a", "9", out_path,
            ],
            check=True, capture_output=True,
        )

    def _duracao_do_arquivo(self, path: str) -> float:
        resultado = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            check=True, capture_output=True, text=True,
        )
        return float(resultado.stdout.strip())
