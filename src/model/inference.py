import os
import time

# 是否启用AI模型（设为False使用纯FAQ模式）
AI_MODEL_ENABLED = False

if AI_MODEL_ENABLED:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
else:
    torch = None
    AutoTokenizer = None
    AutoModelForCausalLM = None
    GenerationConfig = None

import config.config as cfg


class QwenInference:
    def __init__(self, model_path: str = None):
        self.model_path = model_path or cfg.QWEN_MODEL_PATH
        self.max_new_tokens = cfg.QWEN_MAX_NEW_TOKENS
        self.temperature = cfg.QWEN_TEMPERATURE
        self.tokenizer = None
        self.model = None
        self.is_loaded = False

    def load_model(self):
        if self.is_loaded:
            return
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        print(f"Loading Qwen model from {self.model_path}...")
        start_time = time.time()
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_path,
            trust_remote_code=True
        )
        
        if cfg.QWEN_MODEL_QUANTIZED:
            try:
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(load_in_4bit=True)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    device_map="cpu",
                    quantization_config=quantization_config,
                    trust_remote_code=True
                )
            except Exception as e:
                print(f"4bit quantization failed: {e}, using fp16...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_path,
                    device_map="cpu",
                    torch_dtype=torch.float16,
                    trust_remote_code=True
                )
        else:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map="cpu",
                torch_dtype=torch.float32,
                trust_remote_code=True
            )
        
        self.model.eval()
        
        elapsed = time.time() - start_time
        print(f"Model loaded successfully in {elapsed:.2f} seconds")
        self.is_loaded = True

    def unload_model(self):
        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        self.is_loaded = False
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def generate(self, prompt: str, history: Optional[List[Dict]] = None) -> str:
        if not self.is_loaded:
            self.load_model()
        
        messages = []
        
        if history:
            for msg in history[-cfg.CONTEXT_MAX_ROUNDS:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        messages.append({"role": "user", "content": prompt})
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer([text], return_tensors="pt").to("cpu")
        
        generation_config = GenerationConfig(
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            do_sample=True,
            top_p=0.8,
            repetition_penalty=1.1,
        )
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                generation_config=generation_config
            )
        
        response = self.tokenizer.decode(
            outputs[0][len(inputs.input_ids[0]):],
            skip_special_tokens=True
        )
        
        return response.strip()

    def is_ready(self) -> bool:
        return self.is_loaded


_qwen_instance = None


def get_qwen_instance() -> QwenInference:
    global _qwen_instance
    if _qwen_instance is None:
        _qwen_instance = QwenInference()
    return _qwen_instance
