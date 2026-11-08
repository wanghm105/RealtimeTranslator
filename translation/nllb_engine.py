import ctranslate2
from transformers import AutoTokenizer


class NLLBTranslator:

    # 不支持流式输出（一次性出整句，速度极快）
    streaming = False

    def __init__(self):

        print("Loading NLLB translator...")


        self.tokenizer = AutoTokenizer.from_pretrained(
            "models/nllb-tokenizer",
            src_lang="eng_Latn"
        )


        self.model = ctranslate2.Translator(
            "models/nllb-ct2",
            device="cuda",
            compute_type="float16"
        )


        self.target_lang = "zho_Hans"


        print("NLLB ready.")


    def translate(self, text, on_partial=None):

        if not text.strip():
            return ""


        inputs = self.tokenizer(
            text,
            return_tensors=None
        )


        source_tokens = self.tokenizer.convert_ids_to_tokens(
            inputs["input_ids"]
        )


        target_token_id = self.tokenizer.convert_tokens_to_ids(
            self.target_lang
        )


        target_token = self.tokenizer.convert_ids_to_tokens(
            [target_token_id]
        )


        results = self.model.translate_batch(
            [source_tokens],
            target_prefix=[
                target_token
            ]
        )


        output_tokens = results[0].hypotheses[0]


        output_ids = self.tokenizer.convert_tokens_to_ids(
            output_tokens
        )


        return self.tokenizer.decode(
            output_ids,
            skip_special_tokens=True
        )