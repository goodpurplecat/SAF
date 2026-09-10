"""
IA EDITORA — Departamento de Edição

Monta o vídeo final a partir dos slides já renderizados (imagem + áudio +
duração, um por bloco do roteiro) + a música de fundo. É montagem mecânica
(ffmpeg), sem julgamento de IA nenhum — segue exatamente o "sanduíche"
descrito pelo analista (05/09/2026): imagem na tela pelo tempo do áudio +
narração + música de fundo no volume já definido + fade in/out entre
slides + fade in/out geral do vídeo.

A revisão de verdade (comparar o vídeo final com o roteiro aprovado) é
feita depois, pela IA Fiscal de Produção (fiscal_producao_final.py).
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from .design_config import VIDEO_SPEC, TRANSICOES, AUDIO_CONFIG
from .models import SlideRenderizado


def _ffprobe_duracao(path: str) -> float:
    resultado = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        check=True, capture_output=True, text=True,
    )
    return float(resultado.stdout.strip())


def _build_slide_clip(image_path: str, audio_path: str, duracao: float, out_path: str) -> None:
    """Um slide = imagem parada + narração, com fade in/out de entrada/saída do próprio slide."""
    fade_s = TRANSICOES["duracao_slide_s"]
    fade_out_inicio = max(duracao - fade_s, 0)
    largura, altura = VIDEO_SPEC["resolucao"]
    vf = f"fade=t=in:st=0:d={fade_s}:color=black,fade=t=out:st={fade_out_inicio}:d={fade_s}:color=black"

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-t", str(duracao),
            "-vf", f"scale={largura}:{altura},{vf}",
            "-r", str(VIDEO_SPEC["framerate"]),
            "-pix_fmt", "yuv420p",
            "-c:v", VIDEO_SPEC["codec_video"],
            "-c:a", VIDEO_SPEC["codec_audio"],
            "-b:v", VIDEO_SPEC["bitrate_video"],
            "-b:a", VIDEO_SPEC["bitrate_audio"],
            "-shortest",
            out_path,
        ],
        check=True, capture_output=True,
    )


def _concat_clips(clip_paths: List[str], out_path: str, tmp_dir: str) -> None:
    filelist_path = f"{tmp_dir}/filelist.txt"
    with open(filelist_path, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{Path(clip).resolve()}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", filelist_path, "-c", "copy", out_path],
        check=True, capture_output=True,
    )


def _finalizar_com_musica_e_fade(video_sem_musica: str, out_path: str, musica_path: Optional[str]) -> None:
    duracao_total = _ffprobe_duracao(video_sem_musica)
    fade_geral = TRANSICOES["duracao_geral_s"]
    fade_out_inicio = max(duracao_total - fade_geral, 0)
    vf_geral = f"fade=t=in:st=0:d={fade_geral},fade=t=out:st={fade_out_inicio}:d={fade_geral}"

    if not musica_path:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_sem_musica, "-vf", vf_geral,
             "-c:v", VIDEO_SPEC["codec_video"], "-c:a", "copy", out_path],
            check=True, capture_output=True,
        )
        return

    musica_cfg = AUDIO_CONFIG["musica_background"]
    volume_frac = musica_cfg["volume_pct"] / 100
    fade_in_musica = musica_cfg["fade_in_s"]
    fade_out_musica_inicio = max(duracao_total - musica_cfg["fade_out_s"], 0)

    filtro = (
        f"[1:a]volume={volume_frac},afade=t=in:st=0:d={fade_in_musica},"
        f"afade=t=out:st={fade_out_musica_inicio}:d={musica_cfg['fade_out_s']}[musica];"
        f"[0:a][musica]amix=inputs=2:duration=first:dropout_transition=0[audio_final];"
        f"[0:v]{vf_geral}[video_final]"
    )

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_sem_musica,
            "-stream_loop", "-1", "-i", musica_path,
            "-filter_complex", filtro,
            "-map", "[video_final]", "-map", "[audio_final]",
            "-c:v", VIDEO_SPEC["codec_video"],
            "-c:a", VIDEO_SPEC["codec_audio"],
            "-b:v", VIDEO_SPEC["bitrate_video"],
            "-b:a", VIDEO_SPEC["bitrate_audio"],
            "-shortest",
            out_path,
        ],
        check=True, capture_output=True,
    )


def assemble_video(slides: List[SlideRenderizado], out_path: str, musica_path: Optional[str] = None) -> str:
    """
    Monta o vídeo final: slide-por-slide (imagem + narração + fade) → concatena
    → mixa música de fundo (se houver) → fade in/out geral. Retorna out_path.
    """
    for slide in slides:
        if not slide.audio_path or slide.duracao_segundos is None:
            raise ValueError(f"Slide '{slide.bloco_nome}' não tem áudio/duração — rode a IA de Áudio antes de montar o vídeo.")

    with tempfile.TemporaryDirectory() as tmp:
        clip_paths = []
        for i, slide in enumerate(slides):
            clip_path = f"{tmp}/clip_{i:03d}.mp4"
            _build_slide_clip(slide.imagem_path, slide.audio_path, slide.duracao_segundos, clip_path)
            clip_paths.append(clip_path)

        video_sem_musica = f"{tmp}/sem_musica.mp4"
        _concat_clips(clip_paths, video_sem_musica, tmp)

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        _finalizar_com_musica_e_fade(video_sem_musica, out_path, musica_path)

    return out_path
