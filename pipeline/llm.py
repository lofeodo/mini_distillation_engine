# pipeline/llm.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass(frozen=True)
class GenerationConfig:
    """
    Deterministic generation defaults (CPU-friendly).
    """
    max_new_tokens: int = 256
    do_sample: bool = False          # critical for determinism
    temperature: float = 0.0         # ignored when do_sample=False, but keep explicit
    top_p: float = 1.0
    num_beams: int = 1
    repetition_penalty: float = 1.0


class LocalLLM:
    """
    Minimal local inference wrapper for instruction-tuned causal LMs.
    CPU-only by design (Step 4).
    """

    def __init__(
        self,
        model_name_or_path: str,
        cache_dir: Optional[str] = None,
        seed: int = 0,
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.cache_dir = cache_dir
        self.seed = seed

        # Determinism knobs (CPU)
        torch.manual_seed(seed)

        # Choose device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name_or_path,
            cache_dir=cache_dir,
            use_fast=True,
        )

        dtype = torch.float16 if self.device == "cuda" else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name_or_path,
            cache_dir=cache_dir,
            dtype=dtype,                 # replaces deprecated torch_dtype
            device_map="auto" if self.device == "cuda" else None,
        )
        self.model.eval()

        # Some models don't define pad_token; set safely
        if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        print(f"[LocalLLM] device={self.device} dtype={dtype} model_device={self.model.device}")


    def generate_text(
        self,
        prompt: str,
        gen: GenerationConfig = GenerationConfig(),
    ) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        # Re-seed per call for repeatability
        torch.manual_seed(self.seed)

        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        input_ids = inputs["input_ids"]
        attention_mask = inputs.get("attention_mask", None)

        # Build generation kwargs deterministically.
        # Only include sampling params when sampling is enabled (avoids "temperature ignored" warnings).
        gen_kwargs: Dict[str, Any] = {
            "max_new_tokens": gen.max_new_tokens,
            "do_sample": gen.do_sample,
            "num_beams": gen.num_beams,
            "repetition_penalty": gen.repetition_penalty,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        if gen.do_sample:
            gen_kwargs["temperature"] = gen.temperature
            gen_kwargs["top_p"] = gen.top_p

        with torch.no_grad():
            output_ids = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                **gen_kwargs,
            )

        # Decode only the newly generated portion (cleaner than echoing the prompt)
        generated = output_ids[0][input_ids.shape[-1]:]
        text = self.tokenizer.decode(generated, skip_special_tokens=True)

        return text.strip()


def build_json_only_prompt(user_instruction: str) -> str:
    return (
        "You are a service that outputs ONLY valid JSON.\n"
        "Rules:\n"
        "1) Output must be a single JSON object.\n"
        "2) Do not include any other keys than requested.\n"
        "3) Do not include markdown, code fences, or explanations.\n"
        "4) Your first character must be '{' and your last character must be '}'.\n\n"
        f"Return exactly this JSON object, with no changes:\n{user_instruction}\n"
    )