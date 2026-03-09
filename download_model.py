import os
from huggingface_hub import snapshot_download

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

snapshot_download(
    'Qwen/Qwen1.5-1.8B-Chat',
    local_dir='E:/dingtalk_robot_2.0/models/Qwen1.5-1.8B-Chat'
)
print("Download complete!")
