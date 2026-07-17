import os, struct
from PIL import Image

FRAMES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "promo_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SCALE_W = 960
SCALE_H = 540
FPS = 30
TOTAL_FRAMES = 60

print("Loading and scaling frames...")
frames = []
for i in range(TOTAL_FRAMES):
    path = os.path.join(FRAMES_DIR, f"frame_{i:03d}.png")
    img = Image.open(path).convert("RGB")
    img = img.resize((SCALE_W, SCALE_H), Image.LANCZOS)
    frames.append(img)
    if (i+1)%10 == 0: print(f"  {i+1}/{TOTAL_FRAMES}")

print(f"Frames: {len(frames)}, Size: {SCALE_W}x{SCALE_H}")

# Each frame takes SCALE_W * SCALE_H * 3 bytes
# We'll duplicate each frame 30 times to get 30fps
DUP = FPS  # 30 duplicates per frame = 30fps, 60*30=1800 frames, 60 sec
total_out_frames = TOTAL_FRAMES * DUP
frame_bytes = SCALE_W * SCALE_H * 3
stride = (SCALE_W * 3 + 3) & ~3  # DWORD aligned
row_padding = stride - SCALE_W * 3

print(f"Output frames: {total_out_frames}, each {frame_bytes} bytes")
print(f"Stride: {stride}, row padding: {row_padding}")

BI_RGB = 0
uspf = 1000000 // FPS

out_path = os.path.join(OUTPUT_DIR, "promo_video_uncompressed.avi")
print(f"\nWriting to {out_path}...")

with open(out_path, "wb") as f:
    # Pre-compute total movi size
    chunk_size = 8 + stride * SCALE_H  # each 00dc chunk
    if chunk_size % 2: chunk_size += 1
    movi_data_size = total_out_frames * chunk_size
    
    hdrl_size = 4 + 56 + 4 + 8 + 56 + 8 + 40  # hdrl content
    strl_size = 8 + 56 + 8 + 40  # strl content
    idx1_size = 16 * total_out_frames
    
    # RIFF header
    riff_content_size = 4 + 8 + hdrl_size + 8 + movi_data_size + 8 + idx1_size
    f.write(b"RIFF" + struct.pack("<I", riff_content_size) + b"AVI ")
    
    # hdrl
    f.write(b"LIST" + struct.pack("<I", hdrl_size) + b"hdrl")
    
    # avih
    f.write(b"avih" + struct.pack("<I", 56))
    f.write(struct.pack("<IIII", uspf, 0, 0, 0x10))  # uspf, maxbytes, pad, flags
    f.write(struct.pack("<IIII", total_out_frames, 0, 1, frame_bytes))  # frames, init, streams, bufsize
    f.write(struct.pack("<II", SCALE_W, SCALE_H))
    f.write(struct.pack("<IIII", 0, 0, 0, 0))
    
    # strl
    f.write(b"LIST" + struct.pack("<I", 8 + 56 + 8 + 40) + b"strl")
    
    # strh
    f.write(b"strh" + struct.pack("<I", 56))
    f.write(b"vids" + struct.pack("<I", BI_RGB))  # DIB
    f.write(struct.pack("<III", 0, 0, 0))
    f.write(struct.pack("<II", 1, FPS))  # scale, rate
    f.write(struct.pack("<II", 0, total_out_frames))
    f.write(struct.pack("<I", frame_bytes))
    f.write(struct.pack("<II", -1, 0))
    f.write(struct.pack("<IIII", 0, 0, 0, 0))
    
    # strf (BITMAPINFOHEADER)
    f.write(b"strf" + struct.pack("<I", 40))
    f.write(struct.pack("<II", SCALE_W, SCALE_H))
    f.write(struct.pack("<HH", 1, 24))
    f.write(struct.pack("<II", BI_RGB, frame_bytes))
    f.write(struct.pack("<II", 2835, 2835))  # 72 DPI
    f.write(struct.pack("<II", 0, 0))
    
    # movi
    f.write(b"LIST" + struct.pack("<I", 4 + movi_data_size) + b"movi")
    
    movi_data_start = f.tell()
    offsets = []
    
    for fi in range(TOTAL_FRAMES):
        img = frames[fi]
        pixels = img.tobytes()  # RGBRGB...
        
        for dup in range(DUP):
            offsets.append(f.tell() - movi_data_start)
            f.write(b"00dc")
            chunk_data_size = stride * SCALE_H
            f.write(struct.pack("<I", chunk_data_size))
            
            # Write rows bottom-up (AVI expects bottom-up for positive height)
            for y in range(SCALE_H - 1, -1, -1):
                row_start = y * SCALE_W * 3
                row = pixels[row_start:row_start + SCALE_W * 3]
                f.write(row)
                if row_padding > 0:
                    f.write(b"\x00" * row_padding)
        
        if (fi+1)%10 == 0: print(f"  Written frames up to {(fi+1)*DUP}")
    
    # idx1
    idx1_start = f.tell()
    f.write(b"idx1" + struct.pack("<I", idx1_size))
    
    for i, offset in enumerate(offsets):
        f.write(b"00dc" + struct.pack("<III", 0x10, offset, frame_bytes))

print(f"\nDone!")
print(f"File: {out_path}")
print(f"Size: {os.path.getsize(out_path)/1024/1024:.1f} MB")
print(f"Frames: {total_out_frames}, {FPS} fps, {SCALE_W}x{SCALE_H}")
print(f"Duration: {total_out_frames/FPS:.0f} seconds")
