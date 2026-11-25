import json, sys, time
from faster_whisper import WhisperModel

src, out = sys.argv[1], sys.argv[2]
import subprocess, numpy as np
raw = subprocess.run(["ffmpeg","-v","error","-i",src,"-f","f32le","-ac","1","-ar","16000","-"],capture_output=True,check=True).stdout
audio = np.frombuffer(raw, np.float32)
model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=2)
segs, info = model.transcribe(audio, language="fr", beam_size=1, vad_filter=True,
                              word_timestamps=True, condition_on_previous_text=False)
t0 = time.time()
with open(out, "w") as f:
    for s in segs:
        rec = {"s": round(s.start, 2), "e": round(s.end, 2), "t": s.text.strip(),
               "w": [[round(w.start, 2), round(w.end, 2), w.word] for w in (s.words or [])]}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
print("fini", time.time() - t0)
