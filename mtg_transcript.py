import os
import whisper
import tkinter as tk
from tkinter import filedialog, Text
import datetime
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import ffmpeg
from TkinterDnD2 import DND_FILES, TkinterDnD


def main():

    #GUIウィンドウを作成
    #root = tk.Tk()
    root = TkinterDnD.Tk()

    root.title("文字起こしくんβ版 v0.5")
    root.geometry("640x400")

    #ファイルを指定するボタン
    file_var = tk.StringVar(root)

    file_frame = tk.Frame(root, padx=10)
    file_frame.pack(pady=10, anchor="w")
    
    # ドラッグアンドドロップの機能を追加
    def on_drop(event):
        file_path = event.data
        file_var.set(file_path)
    
    file_frame.drop_target_register(DND_FILES)
    file_frame.dnd_bind('<<Drop>>', on_drop)

    file_label = tk.Label(file_frame, text="動画・音声ファイル")
    file_label.pack(side=tk.LEFT)

    file_button = tk.Button(file_frame, text="参照", command=lambda: open_file_dialog(file_var))
    file_button.pack(side=tk.LEFT)

    chosen_file_label = tk.Label(file_frame, textvariable=file_var, width=60, anchor='w')
    chosen_file_label.pack(side=tk.LEFT,expand=True)

    #モデル選択プルダウン
    model_var = tk.StringVar(root)
    model_var.set("large")
    model_options = ["tiny", "base", "small", "medium", "large"]
    model_frame = tk.Frame(root, padx=10)
    model_frame.pack(pady=10, anchor="w")
    model_label = tk.Label(model_frame, text="音声認識モデルサイズ", anchor='w')
    model_label.pack(side=tk.LEFT)
    model_dropdown = tk.OptionMenu(model_frame, model_var, *model_options)
    model_dropdown.pack(side=tk.LEFT)

    #デバイス選択プルダウン
    device_var = tk.StringVar(root)
    device_var.set("cpu")
    device_options = ["cpu", "cuda"]
    device_frame = tk.Frame(root, padx=10)
    #device_frame.pack(pady=10, anchor="w")
    device_label = tk.Label(device_frame, text="デバイス"+"\n"+"(CPUでOK)", anchor='w')
    #device_label.pack(side=tk.LEFT)
    device_dropdown = tk.OptionMenu(device_frame, device_var, *device_options)
    device_dropdown.pack(side=tk.LEFT)

    #コンソール表示用のTextウィジェット
    console = Text(root, wrap=tk.WORD, height=15, padx=10, pady=10)
    
    #Submitボタン
    submit_button = tk.Button(root, text="文字起こし開始", command=lambda: on_submit(root, console, file_var,model_var,device_var))
    
    submit_button.pack(pady=20)
    console.pack(padx=10, pady=10, fill=tk.BOTH)

    root.mainloop()

def print_to_text_widget(root, console, text):
    console.insert(tk.END, text + "\n")
    console.see(tk.END)
    root.update()

def open_file_dialog(file_var):
    chosen_file = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4"), ("WAV files", "*.wav"), ("MP3 files", "*.mp3")])
    file_var.set(chosen_file)

def transcribe_audio(file_path,selected_model,device):
    
    model = whisper.load_model(selected_model,device=device)
    #deviceはcpu→"cpu" gpu=→cuda"

    result = model.transcribe(file_path, verbose=True, language="ja")
    #verbose=Trueで処理経過の出力

    return result

def mp4_to_audio(selected_file):
    #選択したファイルの拡張子確認
    ext = os.path.splitext(selected_file)

    #動画ファイルからの音声ファイルへの変換
    if ext[1].lower() == ".mp4":

        selected_file_wav = ext[0] + ".wav"
        '''
        if os.path.exists(selected_file_wav):
            raise Exception("既に音声ファイルが存在するため音声ファイルを選択しなおしてください。"+"\n")
        '''
        stream = ffmpeg.input(selected_file)
        ffmpeg.output(stream, selected_file_wav).overwrite_output().run()

        if not os.path.exists(selected_file_wav):
            raise Exception("音声ファイルへの変換に失敗しました"+"\n")

        return selected_file_wav
    
    else:
        return selected_file
    
def remove_silence(selected_file):

    audio = AudioSegment.from_wav(selected_file)
    nonsilent_ranges = detect_nonsilent(audio, min_silence_len=1000, silence_thresh=-40)

    if nonsilent_ranges:
        start_trim = nonsilent_ranges[0][0]
        trimmed_audio = audio[start_trim:]
        trimmed_audio.export(selected_file, format="wav")

def on_submit(root, console, file_var, model_var, device_var):

    selected_file = file_var.get()
    selected_model = model_var.get()
    selected_device = device_var.get()

    if selected_file == "":
        print_to_text_widget(root, console, "ファイルを指定してください。")
        return 
    
    print_to_text_widget(root, console, ">音声ファイルへの変換開始")
    try:
        selected_file = mp4_to_audio(selected_file)
    except Exception as e:
        print_to_text_widget(root, console, str(e))
        return
    print_to_text_widget(root, console, ">音声ファイルへの変換終了"+"\n")

    print_to_text_widget(root, console, ">冒頭無音部分の削除開始")

    remove_silence(selected_file)
    
    print_to_text_widget(root, console, ">冒頭無音部分の削除終了"+"\n")

    print_to_text_widget(root, console, ">文字起こし開始"+"\n"+
                                        "進捗状況は別ウィンドウのターミナルを参照してください。"+"\n"+
                                        "処理を中止したい場合はターミナルでctrl+Cを入力してください。"
                                        )

    result = transcribe_audio(selected_file, selected_model, selected_device)

    output_file_name = output_txt(result)
    print_to_text_widget(root, console, ">文字起こし終了"+"\n"+output_file_name+"\n")

def output_txt(result):

    # 保存先ディレクトリを生成
    save_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(save_dir, exist_ok=True)

    # 現在の日付と時間をファイル名に含める
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y%m%d_%H%M%S")
    output_file_name = os.path.join(save_dir, f"Transcript_{formatted_time}.txt")

    # 出力をテキストファイルに保存する
    # 時間とテキストだけを取得してファイルに書き込む
    with open(output_file_name, "w", encoding="utf-8") as output_file:
        for segment in result["segments"]:
            start_time = segment["start"]
            end_time = segment["end"]
            text = segment["text"]
            output_file.write(f"[{start_time} --> {end_time}] {text}\n")
    return output_file_name

if __name__=='__main__':
    main()