import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp
import os
import threading
import queue

formatos_disponiveis = []
fila = queue.Queue()


def centralizar_janela(janela):
    largura = min(820, janela.winfo_screenwidth() - 80)
    altura = min(680, janela.winfo_screenheight() - 80)

    x = (janela.winfo_screenwidth() // 2) - (largura // 2)
    y = (janela.winfo_screenheight() // 2) - (altura // 2)

    janela.geometry(f"{largura}x{altura}+{x}+{y}")
    janela.minsize(650, 560)


def enviar_interface(tipo, dados):
    fila.put((tipo, dados))


def processar_fila():
    while not fila.empty():
        tipo, dados = fila.get()

        if tipo == "progresso":
            barra["value"] = dados["porcentagem"]
            label_porcentagem.config(text=f'{dados["porcentagem"]:.1f}%')
            label_velocidade.config(text=dados["velocidade"])
            label_tempo.config(text=dados["tempo"])
            label_status.config(text=dados["status"])

        elif tipo == "status":
            label_status.config(text=dados)

        elif tipo == "finalizado":
            barra["value"] = 100
            label_porcentagem.config(text="100%")
            label_status.config(text="Download concluído!")
            botao_download.config(state="normal")
            messagebox.showinfo("Finalizado", "Download concluído com sucesso!")

        elif tipo == "erro":
            label_status.config(text="Erro.")
            botao_download.config(state="normal")
            botao_buscar.config(state="normal")
            messagebox.showerror("Erro", dados)

        elif tipo == "info_video":
            label_titulo.config(text=dados["titulo"])
            label_duracao.config(text=dados["duracao"])
            combo_qualidade["values"] = dados["qualidades"]

            if dados["qualidades"]:
                combo_qualidade.current(0)
                label_status.config(text="Qualidades carregadas.")
            else:
                label_status.config(text="Nenhuma qualidade encontrada.")

            botao_buscar.config(state="normal")

    janela.after(100, processar_fila)


def atualizar_progresso(d):
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        baixado = d.get("downloaded_bytes", 0)

        porcentagem = 0
        if total:
            porcentagem = baixado / total * 100

        speed = d.get("speed")
        eta = d.get("eta")

        velocidade = "Velocidade: --"
        tempo = "Tempo restante: --"

        if speed:
            velocidade = f"Velocidade: {speed / 1024 / 1024:.2f} MB/s"

        if eta:
            minutos = eta // 60
            segundos = eta % 60
            tempo = f"Tempo restante: {minutos:02d}:{segundos:02d}"

        enviar_interface(
            "progresso",
            {
                "porcentagem": porcentagem,
                "velocidade": velocidade,
                "tempo": tempo,
                "status": "Baixando...",
            },
        )

    elif d["status"] == "finished":
        enviar_interface(
            "progresso",
            {
                "porcentagem": 100,
                "velocidade": "Velocidade: --",
                "tempo": "Tempo restante: 00:00",
                "status": "Processando arquivo...",
            },
        )


def buscar_qualidades_thread():
    threading.Thread(target=buscar_qualidades, daemon=True).start()


def buscar_qualidades():
    global formatos_disponiveis

    url = entrada_link.get().strip()

    if not url:
        messagebox.showerror("Erro", "Cole o link do vídeo.")
        return

    botao_buscar.config(state="disabled")
    label_status.config(text="Buscando informações...")

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        titulo = info.get("title", "Título não encontrado")

        duracao_seg = info.get("duration")
        if duracao_seg:
            minutos = duracao_seg // 60
            segundos = duracao_seg % 60
            duracao = f"Duração: {minutos}:{segundos:02d}"
        else:
            duracao = "Duração: --"

        formatos_disponiveis.clear()
        qualidades = []

        tipo = combo_tipo.get()

        if tipo == "MP4":
            vistos = set()

            for f in info["formats"]:
                if f.get("vcodec") != "none" and f.get("height"):
                    altura = f.get("height")
                    fps = f.get("fps") or ""
                    ext = f.get("ext", "").upper()
                    codec = f.get("vcodec", "")

                    chave = f"{altura}-{fps}-{ext}-{codec}"

                    if chave in vistos:
                        continue

                    vistos.add(chave)

                    texto = f"{f['format_id']} - {altura}p"

                    if fps:
                        texto += f" {fps}fps"

                    texto += f" • {ext}"

                    if codec:
                        texto += f" • {codec}"

                    tamanho = f.get("filesize") or f.get("filesize_approx")
                    if tamanho:
                        texto += f" • {tamanho / 1024 / 1024:.1f} MB"

                    qualidades.append(texto)
                    formatos_disponiveis.append(f["format_id"])

        else:
            qualidades = ["320 kbps", "192 kbps", "128 kbps"]

        enviar_interface(
            "info_video",
            {
                "titulo": titulo,
                "duracao": duracao,
                "qualidades": qualidades,
            },
        )

    except Exception as e:
        enviar_interface("erro", str(e))


def baixar_thread():
    threading.Thread(target=baixar, daemon=True).start()


def baixar():
    url = entrada_link.get().strip()
    tipo = combo_tipo.get()
    qualidade = combo_qualidade.get()

    if not url:
        messagebox.showerror("Erro", "Cole o link do vídeo.")
        return

    if not qualidade:
        messagebox.showerror("Erro", "Clique em Buscar qualidades primeiro.")
        return

    pasta_destino = filedialog.askdirectory(title="Escolha onde deseja salvar")

    if not pasta_destino:
        return

    botao_download.config(state="disabled")
    barra["value"] = 0
    label_porcentagem.config(text="0%")
    label_velocidade.config(text="Velocidade: --")
    label_tempo.config(text="Tempo restante: --")
    label_status.config(text="Iniciando download...")

    try:
        if tipo == "MP3":
            bitrate = qualidade.replace(" kbps", "")

            opcoes = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(pasta_destino, "%(title)s.%(ext)s"),
                "progress_hooks": [atualizar_progresso],
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": bitrate,
                    }
                ],
            }

        else:
            index = combo_qualidade.current()
            format_id = formatos_disponiveis[index]

            opcoes = {
                "format": f"{format_id}+bestaudio/best",
                "merge_output_format": "mp4",
                "outtmpl": os.path.join(pasta_destino, "%(title)s.%(ext)s"),
                "progress_hooks": [atualizar_progresso],
            }

        with yt_dlp.YoutubeDL(opcoes) as ydl:
            ydl.download([url])

        enviar_interface("finalizado", None)

    except Exception as e:
        enviar_interface("erro", str(e))


janela = tk.Tk()
janela.title("YouTube Downloader")
janela.configure(bg="#0f172a")
centralizar_janela(janela)

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "TCombobox",
    fieldbackground="#1e293b",
    background="#1e293b",
    foreground="white",
    arrowcolor="white",
)

style.configure(
    "Horizontal.TProgressbar",
    troughcolor="#1e293b",
    background="#22c55e",
    thickness=22,
)

container = tk.Frame(janela, bg="#0f172a")
container.pack(fill="both", expand=True, padx=25, pady=20)

titulo = tk.Label(
    container,
    text="🎬 YouTube Downloader",
    bg="#0f172a",
    fg="white",
    font=("Segoe UI", 24, "bold"),
)
titulo.pack()

subtitulo = tk.Label(
    container,
    text="Baixe vídeos em MP4 ou músicas em MP3",
    bg="#0f172a",
    fg="#94a3b8",
    font=("Segoe UI", 11),
)
subtitulo.pack(pady=(0, 15))

card = tk.Frame(container, bg="#111827", padx=25, pady=20)
card.pack(fill="both", expand=True)

tk.Label(
    card,
    text="Link do vídeo",
    bg="#111827",
    fg="white",
    font=("Segoe UI", 10, "bold"),
).pack(anchor="w")

entrada_link = tk.Entry(
    card,
    bg="#1e293b",
    fg="white",
    insertbackground="white",
    relief="flat",
    font=("Segoe UI", 11),
)
entrada_link.pack(fill="x", ipady=10, pady=(5, 15))

label_titulo = tk.Label(
    card,
    text="Título do vídeo aparecerá aqui",
    bg="#111827",
    fg="white",
    font=("Segoe UI", 13, "bold"),
    wraplength=700,
    justify="left",
)
label_titulo.pack(anchor="w")

label_duracao = tk.Label(
    card,
    text="Duração: --",
    bg="#111827",
    fg="#94a3b8",
    font=("Segoe UI", 10),
)
label_duracao.pack(anchor="w", pady=(5, 15))

linha_opcoes = tk.Frame(card, bg="#111827")
linha_opcoes.pack(fill="x", pady=5)

frame_tipo = tk.Frame(linha_opcoes, bg="#111827")
frame_tipo.pack(side="left", fill="x", expand=True)

tk.Label(
    frame_tipo,
    text="Formato",
    bg="#111827",
    fg="white",
    font=("Segoe UI", 10, "bold"),
).pack(anchor="w")

combo_tipo = ttk.Combobox(
    frame_tipo,
    values=["MP4", "MP3"],
    state="readonly",
)
combo_tipo.current(0)
combo_tipo.pack(fill="x", ipady=6, pady=(5, 0))

frame_qualidade = tk.Frame(linha_opcoes, bg="#111827")
frame_qualidade.pack(side="left", fill="x", expand=True, padx=20)

tk.Label(
    frame_qualidade,
    text="Qualidade",
    bg="#111827",
    fg="white",
    font=("Segoe UI", 10, "bold"),
).pack(anchor="w")

combo_qualidade = ttk.Combobox(
    frame_qualidade,
    state="readonly",
)
combo_qualidade.pack(fill="x", ipady=6, pady=(5, 0))

botao_buscar = tk.Button(
    linha_opcoes,
    text="Buscar qualidades",
    command=buscar_qualidades_thread,
    bg="#2563eb",
    fg="white",
    relief="flat",
    font=("Segoe UI", 10, "bold"),
    padx=20,
    pady=9,
    cursor="hand2",
)
botao_buscar.pack(side="right", pady=(20, 0))

barra = ttk.Progressbar(
    card,
    orient="horizontal",
    mode="determinate",
    style="Horizontal.TProgressbar",
)
barra.pack(fill="x", pady=(35, 8))

label_porcentagem = tk.Label(
    card,
    text="0%",
    bg="#111827",
    fg="#22c55e",
    font=("Segoe UI", 13, "bold"),
)
label_porcentagem.pack()

linha_status = tk.Frame(card, bg="#111827")
linha_status.pack(fill="x", pady=(5, 8))

label_velocidade = tk.Label(
    linha_status,
    text="Velocidade: --",
    bg="#111827",
    fg="#94a3b8",
    font=("Segoe UI", 10),
)
label_velocidade.pack(side="left")

label_tempo = tk.Label(
    linha_status,
    text="Tempo restante: --",
    bg="#111827",
    fg="#94a3b8",
    font=("Segoe UI", 10),
)
label_tempo.pack(side="right")

label_status = tk.Label(
    card,
    text="Aguardando link...",
    bg="#111827",
    fg="#94a3b8",
    font=("Segoe UI", 10),
)
label_status.pack(pady=(0, 10))

botao_download = tk.Button(
    janela,
    text="⬇ FAZER DOWNLOAD",
    command=baixar_thread,
    bg="#22c55e",
    fg="white",
    activebackground="#16a34a",
    activeforeground="white",
    relief="flat",
    font=("Segoe UI", 16, "bold"),
    padx=40,
    pady=16,
    cursor="hand2",
)
botao_download.pack(fill="x", padx=25, pady=(0, 20))

processar_fila()
janela.mainloop()
