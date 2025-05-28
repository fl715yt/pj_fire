import os
import json

# ✅ CONFIG
INPUT_FILE = "conversations.json"
MAX_CHUNK_SIZE_MB = 4
OUTPUT_PREFIX = "pj_conversations_part"

def split_conversations(input_file, max_chunk_size_mb):
    with open(input_file, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    chunk = []
    chunk_size = 0
    chunk_count = 1
    max_bytes = max_chunk_size_mb * 1024 * 1024

    def save_chunk(chunk, count):
        out_name = f"{OUTPUT_PREFIX}{count}.json"
        with open(out_name, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
        print(f"✅ Saved {out_name} ({len(chunk)} conversations)")

    for convo in conversations:
        convo_bytes = len(json.dumps(convo, ensure_ascii=False).encode("utf-8"))

        if chunk_size + convo_bytes > max_bytes:
            save_chunk(chunk, chunk_count)
            chunk = []
            chunk_size = 0
            chunk_count += 1

        chunk.append(convo)
        chunk_size += convo_bytes

    if chunk:
        save_chunk(chunk, chunk_count)

if __name__ == "__main__":
    if not os.path.exists(INPUT_FILE):
        print(f"❌ File not found: {INPUT_FILE}")
    else:
        split_conversations(INPUT_FILE, MAX_CHUNK_SIZE_MB)
